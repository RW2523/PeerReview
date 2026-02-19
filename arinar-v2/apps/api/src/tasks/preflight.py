"""
Preflight Orchestrator Tasks
Prepares agents before debate starts by generating prep packs
"""

import psycopg2
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from psycopg2.extras import Json

from src.config import settings
from src.database import get_cursor
from src.services.memory_retrieval import retrieve_allowed_chunks

# Try to import web search
try:
    from duckduckgo_search import DDGS
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False
    DDGS = None

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
        
        # Broadcast progress event via WebSocket
        _broadcast_preflight_progress(debate_id, participant_id, 'running', 'Reading materials and context')
        
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
        model_id = agent_config.get('model_id', 'openai/gpt-4o-mini')  # Cost-optimized: $0.15/$0.60 (was $3/$15!)
        system_prompt = agent_config.get('system_prompt', '')
        model_config = agent_config.get('model_config', {})
        agent_name = agent_config.get('name', 'Participant')
        role_description = agent_config.get('role_description') or agent_config.get('role') or agent_name
        
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
        
        # 3. Perform web research (if available and debate is recent/current topic)
        web_research_results = ""
        web_search_urls = []  # Store URLs separately for metadata
        web_search_data = []  # Store full structured results
        
        if WEB_SEARCH_AVAILABLE and problem_statement:
            try:
                # Broadcast progress: Researching online
                _broadcast_preflight_progress(debate_id, participant_id, 'running', 'Researching topic online')
                
                # Generate HIGHLY PERSONA-SPECIFIC search query based on agent's unique role and perspective
                role_name = role_description or "analyst"
                
                # Extract key persona traits from system prompt for MORE unique searches
                persona_keywords = ""
                if system_prompt:
                    # Extract distinctive keywords from persona (focus words like "skeptical", "data-driven", "emotional", etc.)
                    prompt_lower = system_prompt.lower()
                    distinctive_traits = []
                    trait_words = ['skeptical', 'analytical', 'emotional', 'data', 'strategic', 'critical', 
                                   'creative', 'pragmatic', 'idealistic', 'technical', 'philosophical', 
                                   'economic', 'social', 'political', 'scientific', 'historical']
                    for trait in trait_words:
                        if trait in prompt_lower:
                            distinctive_traits.append(trait)
                    if distinctive_traits:
                        persona_keywords = " ".join(distinctive_traits[:3])  # Use up to 3 distinctive traits
                
                # Clean and enhance query for better search results
                query_base = problem_statement
                
                # Remove question words and generic adjectives that confuse search
                words_to_remove = ['what', 'how', 'why', 'when', 'where', 'which', 'who', 'is', 'are', 
                                  'does', 'do', 'can', 'should', 'would', 'could',
                                  'the', 'a', 'an', 'most', 'best', 'likely', 'potential',
                                  'effective', 'good', 'better', 'ideal', 'optimal']
                
                # Split into words and filter
                words = query_base.split()
                cleaned_words = [w for w in words if w.lower() not in words_to_remove]
                query_base = ' '.join(cleaned_words)
                
                # Add context hints for better results
                # Detect common patterns and add specificity
                query_lower = query_base.lower()
                context_hints = []
                
                # Political/election context
                if any(term in query_lower for term in ['president', 'election', 'candidate', 'nomination', 'campaign']):
                    import datetime
                    current_year = datetime.datetime.now().year
                    context_hints.append(f"USA {current_year} {current_year+1}")
                
                # Medical/health context  
                if any(term in query_lower for term in ['patient', 'disease', 'treatment', 'medical', 'health']):
                    context_hints.append("medical research clinical guidelines")
                
                # Tech context
                if any(term in query_lower for term in ['software', 'ai', 'technology', 'algorithm', 'code']):
                    context_hints.append("technology industry latest")
                
                # Build final search query with context
                context_str = ' '.join(context_hints)
                if persona_keywords:
                    search_query = f"{query_base[:100]} {context_str} {role_name} {persona_keywords}"
                else:
                    search_query = f"{query_base[:100]} {context_str} {role_name} analysis"
                
                print(f"    🔍 Persona-specific web search ({role_name})")
                print(f"    📝 Query: {search_query[:150]}")
                
                with DDGS() as ddgs:
                    # Search for top results
                    results = list(ddgs.text(search_query, max_results=5))  # Get 5 best results
                    
                    if results:
                        web_research_results = "\n**Web Research Results** (Full content from top sources):\n"
                        
                        # Use Jina Reader to fetch FULL content from top 3 sources
                        import requests
                        jina_api_key = "jina_cc6446808d1742868f3d236b28ce09408nTRb3eRDPWIDA6ePEXFgKpHty2a"
                        sources_fetched = 0
                        
                        for i, result in enumerate(results[:3], 1):  # Top 3 for full content
                            title = result.get('title', 'N/A')
                            snippet = result.get('body', '')[:200]
                            url = result.get('href', '')
                            
                            # Try to fetch full content with Jina Reader
                            try:
                                print(f"    📖 Reading full content from: {url[:60]}...")
                                headers = {
                                    'Authorization': f'Bearer {jina_api_key}',
                                    'X-Return-Format': 'markdown',
                                    'X-Timeout': '5'  # 5 second timeout
                                }
                                jina_response = requests.get(
                                    f'https://r.jina.ai/{url}',
                                    headers=headers,
                                    timeout=6
                                )
                                
                                if jina_response.status_code == 200:
                                    full_content = jina_response.text[:3000]  # First 3000 chars
                                    web_research_results += f"{i}. **{title}**\n   URL: {url}\n\n{full_content}\n\n---\n\n"
                                    sources_fetched += 1
                                else:
                                    # Fallback to snippet
                                    web_research_results += f"{i}. **{title}**\n   {snippet}...\n   Source: {url}\n\n"
                                    print(f"       ⚠️ Jina fetch failed ({jina_response.status_code}), using snippet")
                            except Exception as e:
                                # Fallback to snippet if Jina fails
                                web_research_results += f"{i}. **{title}**\n   {snippet}...\n   Source: {url}\n\n"
                                print(f"       ⚠️ Jina error: {str(e)[:50]}, using snippet")
                            
                            # Store structured data
                            web_search_urls.append(url)
                            web_search_data.append({
                                'title': title,
                                'snippet': snippet,
                                'url': url
                            })
                        
                        # Add remaining results as snippets only
                        for i, result in enumerate(results[3:], 4):
                            title = result.get('title', 'N/A')
                            snippet = result.get('body', '')[:200]
                            url = result.get('href', '')
                            web_research_results += f"{i}. **{title}**\n   {snippet}...\n   Source: {url}\n\n"
                            web_search_urls.append(url)
                            web_search_data.append({
                                'title': title,
                                'snippet': snippet,
                                'url': url
                            })
                        
                        print(f"    ✅ Fetched full content from {sources_fetched}/3 sources, {len(results)} total results")
                        print(f"    🔗 First 3 URLs: {', '.join(web_search_urls[:3])}")
                    else:
                        print(f"    ℹ️ No web search results found")
            except Exception as e:
                print(f"    ⚠️ Web search failed: {e}")
                web_research_results = ""
        
        # 3b. Build prep prompt
        # Get current date/time for temporal context
        current_datetime = datetime.utcnow()
        current_date_str = current_datetime.strftime("%A, %B %d, %Y")
        current_time_str = current_datetime.strftime("%I:%M %p UTC")
        
        prep_prompt = f"""You are preparing for an important strategic discussion.

**Current Date & Time**: {current_date_str} at {current_time_str}

**Discussion Title**: {debate_title}

**Your Role**: {system_prompt[:200] if system_prompt else 'Strategic advisor'}

**Problem Statement**:
{problem_statement}

**Available Materials**:
{materials_context if materials_context else 'No materials provided.'}

**Imported Context from Prior Meetings**:
{imported_context if imported_context else 'No prior context imported.'}

{web_research_results if web_research_results else '**No web research performed for this preparation.**'}

**Task**: Generate YOUR preparation memo (400-600 words) in YOUR voice and perspective covering:
1. Key facts and insights - analyze and synthesize findings from ALL web research sources through YOUR lens
2. Potential risks or concerns based on YOUR expertise
3. Open questions YOU want to explore
4. YOUR initial position/recommendations (but remain open-minded)

**CRITICAL INSTRUCTIONS**: 
- STAY IN CHARACTER - this memo should reflect YOUR unique perspective, analytical style, and personality
- ALWAYS consider the current date ({current_date_str}) when analyzing information
- If web research results are provided above (multiple sources), you MUST:
  * Apply YOUR expertise to analyze patterns and themes across ALL sources
  * Cite multiple sources with their URLs throughout your memo
  * Use YOUR analytical framework to note conflicting information
  * Reference at least 5-7 key sources analyzed through YOUR perspective
- Use inline citations like: "According to [source title] (URL), ..."
- Your memo should demonstrate YOUR unique analytical approach and voice
- This prep work is PRIVATE to you - other participants will NOT see this
- During the debate, you can only reference what others have actually said"""
        
        # 4. Call OpenRouter to generate prep pack
        # For V1, use a simple synchronous call (no streaming)
        # In production, you'd get the OpenRouter key from debate policy or user
        # For now, we'll simulate or use a test key
        
        # Get OpenRouter key from policy_config (if exists) or use test mode
        openrouter_key = policy_config.get('openrouter_key') if policy_config else None
        
        # Broadcast progress: Generating insights
        _broadcast_preflight_progress(debate_id, participant_id, 'running', 'Generating strategic insights')
        
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
                
                # Build persona-specific system prompt by COMBINING agent's persona with research instructions
                # This preserves each agent's unique character while ensuring they cite sources
                persona_specific_prompt = f"""{system_prompt if system_prompt else 'You are a strategic advisor.'}

**ADDITIONAL INSTRUCTIONS FOR PREPARATION**:
When preparing for this debate:
1. STAY IN CHARACTER - analyze everything through your unique perspective and personality
2. MUST incorporate web research sources when provided - cite at least 5-7 different sources with URLs
3. Synthesize information across sources using YOUR analytical style
4. Note temporal context - is information current or outdated?
5. Apply YOUR expertise to identify patterns, risks, opportunities based on your role
6. Your memo should be 400-600 words, reference-heavy, and reflect YOUR voice and perspective"""
                
                # Adjust model config for longer, more detailed output
                enhanced_config = model_config.copy()
                enhanced_config['max_tokens'] = 2000  # Allow longer prep packs
                enhanced_config['temperature'] = 0.7  # Balanced creativity
                
                print(f"    🎭 Using persona: {role_description[:50]}...")
                
                response = client.chat_completion(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": persona_specific_prompt},
                        {"role": "user", "content": prep_prompt}
                    ],
                    **enhanced_config
                )
                prep_pack_content = response.get('content', '')
                
                if not prep_pack_content or len(prep_pack_content.strip()) == 0:
                    print(f"    ⚠️ OpenRouter returned empty content! Creating fallback prep pack...")
                    prep_pack_content = f"""**Preparation Memo** (Fallback - OpenRouter returned empty response)

**Current Date**: {current_date_str}

**Role**: {role_description}

**Problem Statement**: {problem_statement[:300]}

**Web Research Summary** ({len(web_search_urls)} sources found):
{"" if not web_search_urls else chr(10).join([f"- {url}" for url in web_search_urls[:5]])}

**Status**: OpenRouter returned an empty response. Web research data was collected but LLM failed to generate prep pack."""
                else:
                    print(f"    ✅ Generated prep pack: {len(prep_pack_content)} chars")
                    
                    # Log if web research was included
                    if web_search_urls:
                        print(f"    📊 Web research was available ({len(web_search_urls)} URLs)")
                        # Check if URLs are actually cited in content
                        citations_found = sum(1 for url in web_search_urls[:3] if url in prep_pack_content)
                        if citations_found == 0:
                            print(f"    ⚠️ WARNING: No web sources were cited in the prep pack content!")
                        else:
                            print(f"    ✓ {citations_found} sources cited in prep pack")
            except Exception as e:
                print(f"    ❌ OpenRouter error: {str(e)}")
                prep_pack_content = f"Error calling OpenRouter: {str(e)}\n\nFallback prep pack with {len(material_chunks)} materials and {len(imported_chunks)} imported chunks."
        
        # 5. Persist prep pack as agent_knowledge_units (TICKET-13C: include retrieval metadata)
        # Extract chunk IDs for provenance
        material_chunk_ids = [str(chunk.chunk_id) for chunk in material_chunks]
        imported_chunk_ids = [str(chunk.chunk_id) for chunk in imported_chunks]
        
        # Use effective_agent_id for knowledge persistence
        # Track whether web research was performed
        web_research_performed = bool(web_research_results and WEB_SEARCH_AVAILABLE)
        
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
                'web_research_performed': web_research_performed,
                'web_research_query': problem_statement[:100] if web_research_performed else None,
                'web_search_urls': web_search_urls,  # List of URLs searched
                'web_search_results': web_search_data,  # Full structured results
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
        
        # Broadcast completion event
        _broadcast_preflight_progress(debate_id, participant_id, 'success', 'Preparation complete')
        
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
            
            # Broadcast failure event
            _broadcast_preflight_progress(debate_id, participant_id, 'failed', f'Error: {str(e)[:100]}')
        except Exception as update_error:
            print(f"    ⚠️  Failed to update participant status: {update_error}")
        raise
    finally:
        cursor.close()
        conn.close()


def _broadcast_preflight_progress(debate_id: str, participant_id: str, status: str, message: str):
    """Helper to broadcast preflight progress events via WebSocket"""
    try:
        from src.websocket_service import websocket_manager
        
        # Create progress event envelope
        event = {
            'type': 'preflight_progress',
            'debate_id': debate_id,
            'participant_id': participant_id,
            'status': status,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Broadcast asynchronously
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(websocket_manager.broadcast_to_debate(debate_id, event))
        else:
            loop.run_until_complete(websocket_manager.broadcast_to_debate(debate_id, event))
    except Exception as e:
        print(f"    ⚠️  Failed to broadcast progress: {e}")


# Create Celery task wrapper if Celery is available
if CELERY_AVAILABLE and celery_app:
    orchestrate_preflight = celery_app.task(name='tasks.preflight.orchestrate_preflight')(orchestrate_preflight_impl)
else:
    # No Celery - use implementation directly
    orchestrate_preflight = orchestrate_preflight_impl
