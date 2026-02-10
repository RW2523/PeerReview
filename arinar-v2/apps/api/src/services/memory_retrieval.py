"""
Memory Retrieval Service
Implements enforcement hook for memory import with auditing
"""

import psycopg2
from datetime import datetime
from typing import List, Optional, Dict, Any
from psycopg2.extras import Json

from src.config import settings
from src.schemas.memory import MemoryChunkResult, MemoryRetrievalResponse


def retrieve_allowed_chunks(
    debate_id: str,
    participant_id: Optional[str],
    query: str,
    top_k: int = 10
) -> MemoryRetrievalResponse:
    """
    Retrieve chunks that a participant is allowed to access
    
    Enforcement rules:
    1. Always include current debate's material chunks (source_debate_id = debate_id, agent_id IS NULL)
    2. Include imported sources ONLY if matching grant exists:
       - scope='all_agents' applies to any participant
       - scope='specific_agents' applies only to granted participant_ids
    3. Log retrieval to memory_access_log with chunk_ids and grant_ids
    
    Retrieval method: Simple keyword scoring over chunk_text (V1)
    
    Args:
        debate_id: Current debate ID
        participant_id: Participant requesting retrieval (None for all)
        query: Search query
        top_k: Maximum chunks to return
    
    Returns:
        MemoryRetrievalResponse with chunks and grant_ids used
    """
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        # 0. Resolve agent_id from participant_id for audit logging
        agent_id_for_logging = None
        if participant_id:
            cursor.execute("""
                SELECT agent_config->>'agent_id' AS agent_id
                FROM participants
                WHERE participant_id = %s
            """, (participant_id,))
            result = cursor.fetchone()
            if result and result[0]:
                agent_id_for_logging = result[0]
        
        # 1. Get allowed source debate IDs based on grants
        allowed_source_debate_ids = [debate_id]  # Always include current debate
        grant_ids_used = []
        
        if participant_id:
            # Check for grants that allow this participant to access imported debates
            cursor.execute("""
                SELECT grant_id, source_debate_id
                FROM debate_memory_grants
                WHERE debate_id = %s
                  AND (
                      scope = 'all_agents'
                      OR (scope = 'specific_agents' AND %s = ANY(allowed_participant_ids))
                  )
                  AND (expires_at IS NULL OR expires_at > NOW())
            """, (debate_id, participant_id))
            
            grants = cursor.fetchall()
            for grant_id, source_debate_id in grants:
                if source_debate_id and source_debate_id not in allowed_source_debate_ids:
                    allowed_source_debate_ids.append(source_debate_id)
                    grant_ids_used.append(grant_id)
        
        # 2. Retrieve chunks using simple keyword scoring
        # V1: Split query into words and count matches (case-insensitive)
        query_words = query.lower().split()
        
        cursor.execute("""
            WITH scored_chunks AS (
                SELECT
                    chunk_id,
                    chunk_text,
                    source_debate_id,
                    agent_id,
                    chunk_metadata,
                    -- Simple keyword scoring: count matches of query words in chunk_text
                    (
                        SELECT COUNT(*)
                        FROM unnest(%s::text[]) AS word
                        WHERE LOWER(chunk_text) LIKE '%%' || word || '%%'
                    ) AS score
                FROM memory_chunks
                WHERE source_debate_id = ANY(%s::uuid[])
                  AND (
                      -- Current debate materials (agent_id IS NULL)
                      (source_debate_id = %s AND agent_id IS NULL)
                      -- Imported debate chunks (if grants exist)
                      OR (source_debate_id != %s)
                  )
            )
            SELECT
                chunk_id,
                chunk_text,
                source_debate_id,
                agent_id,
                chunk_metadata,
                score
            FROM scored_chunks
            WHERE score > 0
            ORDER BY score DESC, chunk_id
            LIMIT %s
        """, (query_words, allowed_source_debate_ids, debate_id, debate_id, top_k))
        
        rows = cursor.fetchall()
        
        # 3. Build response
        chunks = []
        chunk_ids = []
        
        for row in rows:
            chunk_id, chunk_text, source_debate_id, agent_id, chunk_metadata, score = row
            
            chunks.append(MemoryChunkResult(
                chunk_id=chunk_id,
                chunk_text=chunk_text,
                source_debate_id=source_debate_id,
                source_material_id=chunk_metadata.get('material_id') if chunk_metadata else None,
                agent_id=agent_id,
                chunk_metadata=chunk_metadata or {},
                score=float(score)
            ))
            chunk_ids.append(chunk_id)
        
        # 4. Log retrieval to memory_access_log for audit (only if agent_id resolved)
        if agent_id_for_logging:
            cursor.execute("""
                INSERT INTO memory_access_log (
                    access_id,
                    agent_id,
                    debate_id,
                    access_type,
                    query_text,
                    results_count,
                    chunk_ids,
                    metadata,
                    created_at
                ) VALUES (
                    gen_random_uuid(),
                    %s,
                    %s,
                    'retrieval',
                    %s,
                    %s,
                    %s::uuid[],
                    %s,
                    NOW()
                )
            """, (
                agent_id_for_logging,
                debate_id,
                query,
                len(chunks),
                chunk_ids,
                Json({
                    'grant_ids': grant_ids_used,
                    'retrieval_method': 'keyword',
                    'allowed_source_debate_ids': allowed_source_debate_ids
                })
            ))
        
        conn.commit()
        
        return MemoryRetrievalResponse(
            debate_id=debate_id,
            participant_id=participant_id,
            query=query,
            chunks=chunks,
            total_chunks=len(chunks),
            grant_ids_used=grant_ids_used,
            retrieval_method='keyword'
        )
    
    finally:
        cursor.close()
        conn.close()


def check_participant_has_access(
    debate_id: str,
    participant_id: str,
    source_debate_id: str
) -> bool:
    """
    Check if a participant has access to a source debate's memory
    
    Args:
        debate_id: Current debate ID
        participant_id: Participant ID to check
        source_debate_id: Source debate ID to check access for
    
    Returns:
        True if participant has access, False otherwise
    """
    if source_debate_id == debate_id:
        # Always have access to current debate's own materials
        return True
    
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM debate_memory_grants
                WHERE debate_id = %s
                  AND source_debate_id = %s
                  AND (
                      scope = 'all_agents'
                      OR (scope = 'specific_agents' AND %s = ANY(allowed_participant_ids))
                  )
                  AND (expires_at IS NULL OR expires_at > NOW())
            )
        """, (debate_id, source_debate_id, participant_id))
        
        result = cursor.fetchone()
        return result[0] if result else False
    
    finally:
        cursor.close()
        conn.close()
