"""
Preflight Orchestrator Tasks
Prepares agents before debate starts by generating prep packs
"""

import psycopg2
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from psycopg2.extras import Json

from src.config import settings
from src.database import get_cursor
from src.services.memory_retrieval import retrieve_allowed_chunks

# Try to import Celery, but make it optional
try:
    from src.celery_app import celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    celery_app = None

# Try to import OpenRouterClient
try:
    from src.openrouter_client import OpenRouterClient
except ImportError:
    OpenRouterClient = None


def orchestrate_preflight_impl(run_id: str, debate_id: str):
    """
    Main orchestrator task for preflight preparation
    
    Fans out to prepare_participant_preflight for each participant
    """
    print(f"🚀 Starting preflight orchestration: run_id={run_id}, debate_id={debate_id}")
    
    conn = psycopg2.connect(settings.database_url)
    cursor = get_cursor(conn)
    
    try:
        # Update run status to running
        cursor.execute("""
            UPDATE preflight_runs
            SET status = 'running', started_at = NOW()
            WHERE run_id = %s
        """, (run_id,))
        conn.commit()
        print(f"✅ Updated preflight run status to 'running'")
        
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
        print(f"📋 Processing {len(participant_runs)} participants...")
        for run in participant_runs:
            participant_run_id = run['participant_run_id']
            participant_id = run['participant_id']
            try:
                print(f"  → Processing participant {participant_id}...")
                prepare_participant_preflight(
                    participant_run_id=participant_run_id,
                    participant_id=participant_id,
                    debate_id=debate_id
                )
                print(f"  ✅ Participant {participant_id} prepared successfully")
            except Exception as e:
                print(f"  ❌ Error preparing participant {participant_id}: {e}")
                import traceback
                traceback.print_exc()
                # Continue with other participants
        
        # Check if all participants completed
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM preflight_participant_runs
            WHERE run_id = %s
            GROUP BY status
        """, (run_id,))
        
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        print(f"📊 Participant status summary: {status_counts}")
        
        # Determine overall run status
        if status_counts.get('failed', 0) > 0 or status_counts.get('running', 0) > 0:
            final_status = 'failed' if status_counts.get('failed', 0) > 0 else 'running'
        else:
            final_status = 'completed'
        
        print(f"🏁 Preflight orchestration complete: status={final_status}")
        
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
    print(f"    🔄 Preparing participant: run_id={participant_run_id}, participant={participant_id}")
    
    conn = psycopg2.connect(settings.database_url)
    cursor = get_cursor(conn)
    
    try:
        # Update participant run status
        cursor.execute("""
            UPDATE preflight_participant_runs
            SET status = 'running', started_at = NOW()
            WHERE participant_run_id = %s
        """, (participant_run_id,))
        conn.commit()
        print(f"    ✓ Status updated to 'running'")
        
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
        
        agent_config = result['agent_config']
        debate_title = result['title']
        policy_config = result['policy_config']
        
        # Extract agent details
        # agent_id can be None for inline agents (created from templates)
        agent_id = agent_config.get('agent_id') if agent_config else None
        model_id = agent_config.get('model_id', 'anthropic/claude-3.5-sonnet')
        system_prompt = agent_config.get('system_prompt', '')
        model_config = agent_config.get('model_config', {})
        agent_name = agent_config.get('name', 'Participant')
        
        # For inline agents (no agent_id), create a temporary agent record
        # This is needed because agent_knowledge_units has a NOT NULL FK to agents table
        if not agent_id:
            # Check if agent already exists for this participant
            cursor.execute("""
                SELECT agent_id FROM agents WHERE agent_id = %s
            """, (participant_id,))
            
            existing_agent = cursor.fetchone()
            
            if not existing_agent:
                # Create agent record using participant_id
                # Get workspace_id from debate
                cursor.execute("""
                    SELECT workspace_id FROM debates WHERE debate_id = %s
                """, (debate_id,))
                workspace_id = cursor.fetchone()['workspace_id']
                
                cursor.execute("""
                    INSERT INTO agents (agent_id, workspace_id, name, system_prompt, model_id, model_config, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    participant_id,
                    workspace_id,
                    f"{agent_name} (Inline)",
                    system_prompt,
                    model_id,
                    Json(model_config) if model_config else None
                ))
                conn.commit()
                print(f"    ✓ Created temporary agent record for inline participant")
            
            agent_id = participant_id
        
        effective_agent_id = agent_id
        print(f"    ✓ Agent identity: id={effective_agent_id}")
        
        # Update participant run with agent_id
        cursor.execute("""
            UPDATE preflight_participant_runs
            SET agent_id = %s
            WHERE participant_run_id = %s
        """, (agent_id, participant_run_id))
        conn.commit()
        
        # 2. Gather context using semantic retrieval (TICKET-13C, TICKET-13C.1)
        print(f"    🔍 Gathering context...")
        problem_statement = policy_config.get('problem_statement', '') if policy_config else ''
        
        # Get pre-computed query embedding from participant_run metadata (BYOK-safe)
        cursor.execute("""
            SELECT metadata FROM preflight_participant_runs WHERE participant_run_id = %s
        """, (participant_run_id,))
        
        run_metadata = cursor.fetchone()
        stored_query_embedding = None
        if run_metadata and run_metadata['metadata']:
            stored_query_embedding = run_metadata['metadata'].get('query_embedding')
        
        # Build semantic query for logging/audit (even if embedding pre-computed)
        semantic_query = f"{problem_statement[:300] if problem_statement else 'context summary'}\n\nRole: {system_prompt[:200]}"
        
        # Retrieve chunks using pre-computed embedding (BYOK-safe: no key needed)
        try:
            memory_retrieval_result = retrieve_allowed_chunks(
                debate_id=debate_id,
                participant_id=participant_id,
                query=semantic_query,
                top_k=15,
                openrouter_key=None,  # Not needed with pre-computed embedding
                use_semantic=True,
                query_embedding=stored_query_embedding  # Use stored embedding
            )
            
            all_chunks = memory_retrieval_result.chunks
            grant_ids_used = memory_retrieval_result.grant_ids_used
            retrieval_method = memory_retrieval_result.retrieval_method
            print(f"    ✓ Retrieved {len(all_chunks)} chunks via {retrieval_method}")
        except Exception as e:
            print(f"    ⚠️  Memory retrieval failed: {e}")
            all_chunks = []
            grant_ids_used = []
            retrieval_method = 'error'
        
        # Separate material chunks from imported chunks for better context presentation
        material_chunks = [c for c in all_chunks if c.source_debate_id == debate_id]
        imported_chunks = [c for c in all_chunks if c.source_debate_id != debate_id]
        
        materials_context = "\n\n".join([
            f"[Material Chunk {i+1}]: {chunk.chunk_text[:500]}"
            for i, chunk in enumerate(material_chunks)
        ])
        
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
            print(f"    📝 Generating placeholder prep pack (no OpenRouter key)")
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
            print(f"    🤖 Calling OpenRouter for prep pack generation...")
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
        
        # 5. Persist prep pack as agent_knowledge_units (TICKET-13C: include retrieval metadata)
        # Extract chunk IDs for provenance
        material_chunk_ids = [str(chunk.chunk_id) for chunk in material_chunks]
        imported_chunk_ids = [str(chunk.chunk_id) for chunk in imported_chunks]
        
        # Use effective_agent_id for knowledge persistence
        cursor.execute("""
            INSERT INTO agent_knowledge_units (
                knowledge_id, agent_id, source_debate_id, knowledge_type, content, metadata, created_at
            ) VALUES (
                gen_random_uuid(), %s, %s, 'prep_pack', %s, %s, NOW()
            )
            RETURNING knowledge_id
        """, (
            effective_agent_id,
            debate_id,
            prep_pack_content,
            Json({
                'created_by': 'preflight',
                'participant_id': participant_id,
                'participant_name': agent_name,
                'is_inline_agent': agent_id is None,
                'material_chunks_count': len(material_chunks),
                'imported_chunks_count': len(imported_chunks),
                'grant_ids_used': grant_ids_used,
                'model_used': model_id,
                'retrieval_method': retrieval_method,
                'material_chunk_ids': material_chunk_ids,
                'imported_chunk_ids': imported_chunk_ids,
                'semantic_query_used': semantic_query[:200],
                'generated_at': datetime.utcnow().isoformat()
            })
        ))
        
        prep_pack_knowledge_id = cursor.fetchone()['knowledge_id']
        print(f"    ✓ Prep pack persisted: knowledge_id={prep_pack_knowledge_id}")
        
        # 6. Update participant run to success (TICKET-13C: include retrieval metadata)
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
                'grants_used': len(grant_ids_used),
                'retrieval_mode': retrieval_method,
                'embeddings_used': retrieval_method == 'semantic',
                'material_chunk_ids': material_chunk_ids,
                'imported_chunk_ids': imported_chunk_ids
            }),
            participant_run_id
        ))
        conn.commit()
        print(f"    ✅ Participant preparation complete!")
        
    except Exception as e:
        # Rollback any failed transaction first
        conn.rollback()
        # Update participant run to failed
        try:
            cursor.execute("""
                UPDATE preflight_participant_runs
                SET status = 'failed', error = %s, completed_at = NOW()
                WHERE participant_run_id = %s
            """, (str(e), participant_run_id))
            conn.commit()
        except Exception as update_error:
            print(f"    ⚠️  Failed to update participant status: {update_error}")
        raise
    finally:
        cursor.close()
        conn.close()


# Create Celery task wrapper if Celery is available
if CELERY_AVAILABLE and celery_app:
    orchestrate_preflight = celery_app.task(name='tasks.preflight.orchestrate_preflight')(orchestrate_preflight_impl)
else:
    # No Celery - use implementation directly
    orchestrate_preflight = orchestrate_preflight_impl
