"""
Preflight Orchestrator Tasks
Prepares agents before debate starts by generating prep packs
"""

import psycopg2
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from psycopg2.extras import Json

from src.celery_app import celery_app
from src.config import settings
from src.services.memory_retrieval import retrieve_allowed_chunks
from src.openrouter_client import OpenRouterClient


@celery_app.task(name='tasks.preflight.orchestrate_preflight')
def orchestrate_preflight(run_id: str, debate_id: str):
    """
    Main orchestrator task for preflight preparation
    
    Fans out to prepare_participant_preflight for each participant
    """
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        # Update run status to running
        cursor.execute("""
            UPDATE preflight_runs
            SET status = 'running', started_at = NOW()
            WHERE run_id = %s
        """, (run_id,))
        conn.commit()
        
        # Get all participants for this run
        cursor.execute("""
            SELECT participant_run_id, participant_id
            FROM preflight_participant_runs
            WHERE run_id = %s AND status = 'queued'
        """, (run_id,))
        
        participant_runs = cursor.fetchall()
        
        if not participant_runs:
            # No participants to process
            cursor.execute("""
                UPDATE preflight_runs
                SET status = 'completed', completed_at = NOW()
                WHERE run_id = %s
            """, (run_id,))
            conn.commit()
            return
        
        # Process each participant synchronously (V1 simplicity)
        # Later: can use Celery group/chord for parallel execution
        for participant_run_id, participant_id in participant_runs:
            try:
                prepare_participant_preflight(
                    participant_run_id=participant_run_id,
                    participant_id=participant_id,
                    debate_id=debate_id
                )
            except Exception as e:
                print(f"Error preparing participant {participant_id}: {e}")
                # Continue with other participants
        
        # Check if all participants completed
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM preflight_participant_runs
            WHERE run_id = %s
            GROUP BY status
        """, (run_id,))
        
        status_counts = dict(cursor.fetchall())
        
        # Determine overall run status
        if status_counts.get('failed', 0) > 0 or status_counts.get('running', 0) > 0:
            final_status = 'failed' if status_counts.get('failed', 0) > 0 else 'running'
        else:
            final_status = 'completed'
        
        cursor.execute("""
            UPDATE preflight_runs
            SET status = %s, completed_at = NOW()
            WHERE run_id = %s
        """, (final_status, run_id))
        conn.commit()
        
    except Exception as e:
        cursor.execute("""
            UPDATE preflight_runs
            SET status = 'failed', error = %s, completed_at = NOW()
            WHERE run_id = %s
        """, (str(e), run_id))
        conn.commit()
        raise
    finally:
        cursor.close()
        conn.close()


def prepare_participant_preflight(participant_run_id: str, participant_id: str, debate_id: str):
    """
    Prepare a single participant for the debate
    
    Steps:
    1. Resolve participant -> agent identity
    2. Gather context (materials + imported memory)
    3. Generate prep pack via OpenRouter
    4. Persist as agent_knowledge_units
    """
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        # Update participant run status
        cursor.execute("""
            UPDATE preflight_participant_runs
            SET status = 'running', started_at = NOW()
            WHERE participant_run_id = %s
        """, (participant_run_id,))
        conn.commit()
        
        # 1. Get participant details and resolve agent
        cursor.execute("""
            SELECT p.agent_config, d.title, d.policy_config
            FROM participants p
            JOIN debates d ON p.debate_id = d.debate_id
            WHERE p.participant_id = %s
        """, (participant_id,))
        
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"Participant {participant_id} not found")
        
        agent_config, debate_title, policy_config = result
        
        # Extract agent details
        agent_id = agent_config.get('agent_id') if agent_config else None
        model_id = agent_config.get('model_id', 'anthropic/claude-3.5-sonnet')
        system_prompt = agent_config.get('system_prompt', '')
        model_config = agent_config.get('model_config', {})
        
        if not agent_id:
            raise ValueError(f"Participant {participant_id} has no agent_id in agent_config")
        
        # Update participant run with agent_id
        cursor.execute("""
            UPDATE preflight_participant_runs
            SET agent_id = %s
            WHERE participant_run_id = %s
        """, (agent_id, participant_run_id))
        conn.commit()
        
        # 2. Gather context
        problem_statement = policy_config.get('problem_statement', '') if policy_config else ''
        
        # Get current debate materials chunks
        cursor.execute("""
            SELECT chunk_id, chunk_text, chunk_metadata
            FROM memory_chunks
            WHERE source_debate_id = %s 
              AND agent_id IS NULL
            ORDER BY created_at DESC
            LIMIT 20
        """, (debate_id,))
        
        material_chunks = cursor.fetchall()
        materials_context = "\n\n".join([
            f"[Material Chunk {i+1}]: {chunk_text[:500]}"
            for i, (_, chunk_text, _) in enumerate(material_chunks)
        ])
        
        # Get imported memory chunks (if grants exist)
        try:
            memory_retrieval_result = retrieve_allowed_chunks(
                debate_id=debate_id,
                participant_id=participant_id,
                query=problem_statement[:200] if problem_statement else "context summary",
                top_k=10
            )
            
            imported_chunks = memory_retrieval_result.chunks
            grant_ids_used = memory_retrieval_result.grant_ids_used
        except Exception as e:
            print(f"Memory retrieval failed for {participant_id}: {e}")
            imported_chunks = []
            grant_ids_used = []
        
        imported_context = "\n\n".join([
            f"[Imported Context {i+1}]: {chunk.chunk_text[:500]}"
            for i, chunk in enumerate(imported_chunks)
        ])
        
        # 3. Build prep prompt
        prep_prompt = f"""You are preparing for an important strategic discussion.

**Discussion Title**: {debate_title}

**Your Role**: {system_prompt[:200] if system_prompt else 'Strategic advisor'}

**Problem Statement**:
{problem_statement}

**Available Materials**:
{materials_context if materials_context else 'No materials provided.'}

**Imported Context from Prior Meetings**:
{imported_context if imported_context else 'No prior context imported.'}

**Task**: Generate a concise preparation memo (200-400 words) covering:
1. Key facts and insights relevant to the problem
2. Potential risks or concerns
3. Open questions to explore
4. Your initial stance or recommendation

Be specific and cite information where possible."""
        
        # 4. Call OpenRouter to generate prep pack
        # For V1, use a simple synchronous call (no streaming)
        # In production, you'd get the OpenRouter key from debate policy or user
        # For now, we'll simulate or use a test key
        
        # Get OpenRouter key from policy_config (if exists) or use test mode
        openrouter_key = policy_config.get('openrouter_key') if policy_config else None
        
        if not openrouter_key:
            # For V1, create a placeholder prep pack (no real OpenRouter call)
            prep_pack_content = f"""**Preparation Memo**

**Role**: {system_prompt[:100] if system_prompt else 'Strategic advisor'}

**Key Context**:
- Problem: {problem_statement[:200] if problem_statement else 'N/A'}
- Materials reviewed: {len(material_chunks)} chunks
- Prior context: {len(imported_chunks)} imported chunks

**Initial Assessment**:
This is a placeholder prep pack generated without OpenRouter key. In production, this would contain:
- Synthesized insights from materials
- Risk analysis
- Open questions
- Initial recommendations

**Status**: Generated successfully with {len(material_chunks)} material chunks and {len(imported_chunks)} imported memory chunks."""
        else:
            # Real OpenRouter call
            try:
                client = OpenRouterClient(api_key=openrouter_key)
                response = client.chat_completion(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": "You are a strategic preparation assistant."},
                        {"role": "user", "content": prep_prompt}
                    ],
                    **model_config
                )
                prep_pack_content = response.get('choices', [{}])[0].get('message', {}).get('content', 'Error generating prep pack')
            except Exception as e:
                prep_pack_content = f"Error calling OpenRouter: {str(e)}\n\nFallback prep pack with {len(material_chunks)} materials and {len(imported_chunks)} imported chunks."
        
        # 5. Persist prep pack as agent_knowledge_units
        cursor.execute("""
            INSERT INTO agent_knowledge_units (
                knowledge_id, agent_id, source_debate_id, knowledge_type, content, metadata, created_at
            ) VALUES (
                gen_random_uuid(), %s, %s, 'prep_pack', %s, %s, NOW()
            )
            RETURNING knowledge_id
        """, (
            agent_id,
            debate_id,
            prep_pack_content,
            Json({
                'created_by': 'preflight',
                'participant_id': participant_id,
                'material_chunks_count': len(material_chunks),
                'imported_chunks_count': len(imported_chunks),
                'grant_ids_used': grant_ids_used,
                'model_used': model_id,
                'generated_at': datetime.utcnow().isoformat()
            })
        ))
        
        prep_pack_knowledge_id = cursor.fetchone()[0]
        
        # 6. Update participant run to success
        cursor.execute("""
            UPDATE preflight_participant_runs
            SET status = 'success', 
                completed_at = NOW(),
                prep_pack_knowledge_id = %s,
                metadata = %s
            WHERE participant_run_id = %s
        """, (
            prep_pack_knowledge_id,
            Json({
                'chunks_processed': len(material_chunks) + len(imported_chunks),
                'grants_used': len(grant_ids_used)
            }),
            participant_run_id
        ))
        conn.commit()
        
    except Exception as e:
        # Update participant run to failed
        cursor.execute("""
            UPDATE preflight_participant_runs
            SET status = 'failed', error = %s, completed_at = NOW()
            WHERE participant_run_id = %s
        """, (str(e), participant_run_id))
        conn.commit()
        raise
    finally:
        cursor.close()
        conn.close()
