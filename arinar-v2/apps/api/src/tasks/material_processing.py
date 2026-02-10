"""
Celery tasks for material processing
Handles file validation, text extraction, chunking, and storage
"""

import json
from datetime import datetime
from typing import Dict
import psycopg2
from psycopg2.extras import Json

from src.celery_app import celery_app
from src.config import settings
from src.utils.storage import get_storage_client
from src.utils.text_extraction import TextExtractor
from src.utils.chunking import TextChunker
from src.database import get_db_connection


@celery_app.task(name="src.tasks.material_processing.process_material", bind=True)
def process_material(self, material_id: str, debate_id: str):
    """
    Main task: Process uploaded material
    
    Steps:
    1. Fetch material metadata from DB
    2. Download file from MinIO
    3. Validate file
    4. Extract text
    5. Chunk text
    6. Store chunks in memory_chunks
    7. Update material status
    
    Args:
        material_id: UUID of material to process
        debate_id: UUID of debate
    """
    task_id = self.request.id
    
    try:
        # 1. Get material metadata
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_key, file_mime_type, title
            FROM meeting_materials
            WHERE material_id = %s AND debate_id = %s
        """, (material_id, debate_id))
        
        result = cursor.fetchone()
        if not result:
            raise Exception(f"Material {material_id} not found")
        
        file_key, mime_type, title = result
        
        # Update status to processing
        _update_material_status(
            conn, material_id, 
            status='processing',
            processing_metadata={'started_at': datetime.utcnow().isoformat()}
        )
        conn.commit()
        
        # 2. Download file from MinIO
        storage_client = get_storage_client()
        file_data = storage_client.download_file(file_key)
        
        # 3. Validate file (double-check even though we validated on upload)
        is_valid, detected_mime, error_msg = TextExtractor.validate_file(file_data, title)
        if not is_valid:
            raise Exception(f"File validation failed: {error_msg}")
        
        # 4. Extract text
        extraction_result = TextExtractor.extract(file_data, mime_type)
        
        # Check if scanned PDF
        if extraction_result.get('is_scanned'):
            _update_material_status(
                conn, material_id,
                status='needs_ocr',
                processing_metadata={
                    'message': 'Scanned PDF detected. OCR required.',
                    'page_count': extraction_result.get('page_count', 0)
                }
            )
            conn.commit()
            return {
                'material_id': material_id,
                'status': 'needs_ocr',
                'message': 'Scanned PDF detected'
            }
        
        text = extraction_result.get('text', '')
        if not text or not text.strip():
            raise Exception("No text extracted from file")
        
        # 5. Chunk text
        chunks = TextChunker.chunk_text(
            text=text,
            material_id=material_id,
            extraction_metadata=extraction_result
        )
        
        if not chunks:
            raise Exception("No chunks generated from text")
        
        # 6. Store chunks in memory_chunks
        chunk_ids = []
        for chunk in chunks:
            cursor.execute("""
                INSERT INTO memory_chunks (
                    chunk_id, agent_id, source_debate_id, chunk_text, chunk_metadata
                )
                VALUES (gen_random_uuid(), NULL, %s, %s, %s)
                RETURNING chunk_id
            """, (
                debate_id,
                chunk['chunk_text'],
                Json(chunk['chunk_metadata'])
            ))
            chunk_id = cursor.fetchone()[0]
            chunk_ids.append(str(chunk_id))
        
        conn.commit()
        
        # 7. Update material status to complete
        processing_metadata = {
            'completed_at': datetime.utcnow().isoformat(),
            'extraction_method': extraction_result.get('extraction_method'),
            'word_count': extraction_result.get('word_count', 0),
            'chunk_count': len(chunks),
            'sha256': extraction_result.get('sha256'),
        }
        
        # Add type-specific metadata
        if extraction_result.get('page_count'):
            processing_metadata['page_count'] = extraction_result['page_count']
        if extraction_result.get('paragraph_count'):
            processing_metadata['paragraph_count'] = extraction_result['paragraph_count']
        if extraction_result.get('line_count'):
            processing_metadata['line_count'] = extraction_result['line_count']
        
        _update_material_status(
            conn, material_id,
            status='complete',
            processing_metadata=processing_metadata,
            processing_completed_at=datetime.utcnow()
        )
        conn.commit()
        
        return {
            'material_id': material_id,
            'status': 'complete',
            'chunk_count': len(chunks),
            'word_count': extraction_result.get('word_count', 0),
            'chunk_ids': chunk_ids[:10]  # Return first 10 for debugging
        }
    
    except Exception as e:
        error_msg = str(e)
        print(f"Error processing material {material_id}: {error_msg}")
        
        # Update status to failed
        if conn:
            try:
                _update_material_status(
                    conn, material_id,
                    status='failed',
                    processing_metadata={
                        'error': error_msg,
                        'failed_at': datetime.utcnow().isoformat()
                    }
                )
                conn.commit()
            except Exception as update_error:
                print(f"Failed to update error status: {update_error}")
        
        # Re-raise to mark Celery task as failed
        raise
    
    finally:
        if conn:
            conn.close()


def _update_material_status(
    conn,
    material_id: str,
    status: str,
    processing_metadata: Dict = None,
    processing_started_at: datetime = None,
    processing_completed_at: datetime = None
):
    """Helper to update material processing status"""
    cursor = conn.cursor()
    
    # Build update query dynamically
    updates = ["processed_status = %s", "updated_at = NOW()"]
    params = [status]
    
    if processing_metadata:
        # Merge with existing metadata
        cursor.execute("""
            SELECT processing_metadata FROM meeting_materials WHERE material_id = %s
        """, (material_id,))
        existing_meta = cursor.fetchone()
        existing_meta = existing_meta[0] if existing_meta else {}
        
        merged_meta = {**existing_meta, **processing_metadata}
        updates.append("processing_metadata = %s")
        params.append(Json(merged_meta))
    
    if processing_started_at:
        updates.append("processing_started_at = %s")
        params.append(processing_started_at)
    
    if processing_completed_at:
        updates.append("processing_completed_at = %s")
        params.append(processing_completed_at)
    
    params.append(material_id)
    
    query = f"""
        UPDATE meeting_materials 
        SET {', '.join(updates)}
        WHERE material_id = %s
    """
    
    cursor.execute(query, params)
