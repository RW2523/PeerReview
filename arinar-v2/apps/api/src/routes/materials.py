"""
Materials upload and status endpoints
"""

import io
import uuid
from datetime import datetime
from typing import List
import psycopg2
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from psycopg2.extras import Json

from src.config import settings
from src.schemas.materials import (
    MaterialUploadResponse,
    MaterialsStatusResponse,
    MaterialStatus,
    MaterialRetryRequest,
    MaterialRetryResponse
)
from src.utils.storage import get_storage_client
from src.utils.text_extraction import TextExtractor
from src.tasks.material_processing import process_material
from src.auth import require_auth

router = APIRouter()


@router.post("/debates/{debate_id}/materials/upload", response_model=MaterialUploadResponse)
async def upload_materials(
    debate_id: str,
    files: List[UploadFile] = File(...),
    _workspace_id: str = Depends(require_auth)
):
    """
    Upload multiple files for a debate
    
    Steps:
    1. Validate file types and sizes
    2. Upload to MinIO
    3. Create meeting_materials rows
    4. Queue Celery processing tasks
    
    Returns:
        MaterialUploadResponse with material IDs and job IDs
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per upload")
    
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    # Verify debate exists and user has access
    cursor.execute("""
        SELECT workspace_id FROM debates WHERE debate_id = %s
    """, (debate_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Debate not found")
    
    db_workspace_id = result[0]
    if str(db_workspace_id) != _workspace_id:
        conn.close()
        raise HTTPException(status_code=403, detail="Access denied to this debate")
    
    material_ids = []
    job_ids = []
    
    try:
        for upload_file in files:
            # Read file contents
            file_contents = await upload_file.read()
            file_size = len(file_contents)
            
            # Validate file
            is_valid, mime_type, error_msg = TextExtractor.validate_file(
                file_contents, upload_file.filename
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{upload_file.filename}' validation failed: {error_msg}"
                )
            
            # Generate file key for MinIO
            material_id = str(uuid.uuid4())
            file_extension = upload_file.filename.split('.')[-1] if '.' in upload_file.filename else 'bin'
            file_key = f"debates/{debate_id}/materials/{material_id}.{file_extension}"
            
            # Upload to MinIO
            try:
                storage_client = get_storage_client()
                storage_client.upload_file(
                    file_key=file_key,
                    file_data=io.BytesIO(file_contents),
                    file_size=file_size,
                    content_type=mime_type
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload file '{upload_file.filename}': {str(e)}"
                )
            
            # Create meeting_materials row
            cursor.execute("""
                INSERT INTO meeting_materials (
                    material_id, debate_id, kind, title,
                    file_key, file_size_bytes, file_mime_type,
                    processed_status, processing_metadata
                )
                VALUES (%s, %s, 'file', %s, %s, %s, %s, 'pending', %s)
                RETURNING material_id
            """, (
                material_id,
                debate_id,
                upload_file.filename,
                file_key,
                file_size,
                mime_type,
                Json({'uploaded_at': datetime.utcnow().isoformat()})
            ))
            
            created_material_id = cursor.fetchone()[0]
            material_ids.append(str(created_material_id))
            
            # Queue Celery task
            task = process_material.delay(str(created_material_id), debate_id)
            job_ids.append(task.id)
        
        conn.commit()
        
        return MaterialUploadResponse(
            material_ids=material_ids,
            job_ids=job_ids,
            total_files=len(files)
        )
    
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        conn.close()


@router.get("/debates/{debate_id}/materials/status", response_model=MaterialsStatusResponse)
async def get_materials_status(
    debate_id: str,
    _workspace_id: str = Depends(require_auth)
):
    """
    Get processing status of all materials in a debate
    
    Returns:
        MaterialsStatusResponse with status for each material
    """
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    # Verify debate exists and user has access
    cursor.execute("""
        SELECT workspace_id FROM debates WHERE debate_id = %s
    """, (debate_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Debate not found")
    
    db_workspace_id = result[0]
    if str(db_workspace_id) != _workspace_id:
        conn.close()
        raise HTTPException(status_code=403, detail="Access denied to this debate")
    
    # Fetch all materials for this debate
    cursor.execute("""
        SELECT 
            material_id, title, kind, file_size_bytes, file_mime_type,
            processed_status, processing_metadata, created_at,
            processing_started_at, processing_completed_at
        FROM meeting_materials
        WHERE debate_id = %s
        ORDER BY created_at DESC
    """, (debate_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    materials = []
    status_summary = {}
    
    for row in rows:
        material = MaterialStatus(
            material_id=str(row[0]),
            title=row[1],
            kind=row[2],
            file_size_bytes=row[3],
            file_mime_type=row[4],
            processed_status=row[5],
            processing_metadata=row[6] or {},
            created_at=row[7],
            processing_started_at=row[8],
            processing_completed_at=row[9]
        )
        materials.append(material)
        
        # Update summary
        status = material.processed_status
        status_summary[status] = status_summary.get(status, 0) + 1
    
    return MaterialsStatusResponse(
        debate_id=debate_id,
        total_materials=len(materials),
        status_summary=status_summary,
        materials=materials
    )


@router.post("/debates/{debate_id}/materials/retry", response_model=MaterialRetryResponse)
async def retry_material_processing(
    debate_id: str,
    request: MaterialRetryRequest,
    _workspace_id: str = Depends(require_auth)
):
    """
    Retry processing a failed material
    
    Args:
        debate_id: Debate UUID
        request: Material ID to retry
    
    Returns:
        MaterialRetryResponse with new job ID
    """
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    # Verify material exists and belongs to debate
    cursor.execute("""
        SELECT processed_status FROM meeting_materials
        WHERE material_id = %s AND debate_id = %s
    """, (request.material_id, debate_id))
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Material not found")
    
    current_status = result[0]
    if current_status not in ['failed', 'needs_ocr']:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry material with status '{current_status}'"
        )
    
    # Reset status to pending
    cursor.execute("""
        UPDATE meeting_materials
        SET processed_status = 'pending',
            processing_metadata = processing_metadata || %s::jsonb,
            updated_at = NOW()
        WHERE material_id = %s
    """, (
        Json({'retry_at': datetime.utcnow().isoformat()}),
        request.material_id
    ))
    conn.commit()
    conn.close()
    
    # Queue new Celery task
    task = process_material.delay(request.material_id, debate_id)
    
    return MaterialRetryResponse(
        material_id=request.material_id,
        job_id=task.id,
        message="Processing retry queued"
    )
