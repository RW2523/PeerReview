"""Host conclusion orchestration - separate from regular turn flow"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
import psycopg2.extras
from .database import get_db_connection, get_cursor
from .openrouter_client import OpenRouterClient


class HostOrchestrator:
    """
    Manages the Ultimate Host conclusion flow
    
    The host is NOT a regular participant - it only speaks at the end
    to provide a neutral, fact-based synthesis of all viewpoints.
    """
    
    def __init__(self, openrouter_api_key: str):
        self.openrouter_client = OpenRouterClient(openrouter_api_key)
    
    def trigger_conclusion(self, debate_id: str) -> Dict[str, Any]:
        """
        Trigger the Ultimate Host to provide final conclusion
        
        Only called after all regular rounds are complete.
        Host synthesizes all viewpoints and provides neutral recommendation.
        
        Returns:
            Dict with event_id, message, etc.
        """
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            # Get debate details
            cursor.execute("""
                SELECT debate_id, title, description, state, policy_config
                FROM debates
                WHERE debate_id = %s
            """, (debate_id,))
            
            debate = cursor.fetchone()
            if not debate:
                raise ValueError(f"Debate {debate_id} not found")
            
            if debate['state'] != 'running':
                raise ValueError(f"Debate must be in 'running' state")
            
            policy_config = debate['policy_config'] or {}
            
            # Verify host is enabled
            if not policy_config.get('enable_host'):
                raise ValueError("Host is not enabled for this debate")
            
            # Check if already concluded
            if policy_config.get('host_concluded'):
                raise ValueError("Host has already provided conclusion")
            
            # Get host model
            host_model_id = policy_config.get('host_model_id', 'openai/gpt-4o-mini')
            
            # Get all participants for @mention list
            cursor.execute("""
                SELECT participant_id, agent_config, role_name
                FROM participants
                WHERE debate_id = %s
                ORDER BY created_at ASC
            """, (debate_id,))
            
            participants = cursor.fetchall()
            participant_names = [
                (p['agent_config'] or {}).get('name') or p['role_name']
                for p in participants
            ]
            
            # Get full debate history
            cursor.execute("""
                SELECT event_type, sender_type, content, created_at
                FROM events
                WHERE debate_id = %s
                ORDER BY sequence_number ASC
            """, (debate_id,))
            
            history_events = cursor.fetchall()
            
            # Build host system prompt from template
            from .agent_templates import get_template_by_id
            host_template = get_template_by_id('ultimate-host')
            if not host_template:
                raise ValueError("Ultimate Host template not found")
            
            host_system_prompt = host_template['system_prompt']
            
            # Build conversation summary for host
            conversation_summary = self._build_host_context(
                debate['title'],
                policy_config.get('desired_outcomes', []),
                participant_names,
                history_events
            )
            
            # Call LLM for host conclusion
            messages = [
                {"role": "system", "content": host_system_prompt},
                {"role": "user", "content": conversation_summary}
            ]
            
            host_response = self.openrouter_client.chat_completion(
                model=host_model_id,
                messages=messages,
                temperature=0.3,  # Low temperature for consistency
                max_tokens=3000
            )
            
            # Persist host conclusion as event
            event_id = str(uuid.uuid4())
            total_turns = policy_config.get('total_turns_taken', 0)
            
            cursor.execute("""
                SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
                FROM events
                WHERE debate_id = %s
            """, (debate_id,))
            next_seq = cursor.fetchone()['next_seq']
            
            cursor.execute("""
                INSERT INTO events (
                    event_id, debate_id, event_type, sender_type, sender_id,
                    sequence_number, content, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                RETURNING event_id, sequence_number
            """, (
                event_id,
                debate_id,
                'agent_message',
                'system',  # Host is system-type
                None,  # No specific participant_id for host
                next_seq,
                psycopg2.extras.Json({
                    'agent_name': 'Ultimate Host',
                    'text': host_response['content'],
                    'model': host_response.get('model', host_model_id),
                    'is_host_conclusion': True
                })
            ))
            
            # Update policy config - mark as concluded
            policy_config['host_concluded'] = True
            policy_config['total_turns_taken'] = total_turns  # Don't increment for host
            
            cursor.execute("""
                UPDATE debates
                SET policy_config = %s, updated_at = NOW()
                WHERE debate_id = %s
            """, (psycopg2.extras.Json(policy_config), debate_id))
            
            return {
                'event_id': event_id,
                'message': host_response['content'],
                'participant_name': 'Ultimate Host',
                'sequence_number': next_seq,
                'is_conclusion': True
            }
    
    def _build_host_context(
        self,
        title: str,
        desired_outcomes: List[str],
        participant_names: List[str],
        events: List[Dict[str, Any]]
    ) -> str:
        """Build context summary for host to analyze"""
        
        # Extract all agent messages
        agent_messages = []
        for event in events:
            if event['event_type'] == 'agent_message':
                content = event.get('content') or {}
                agent_name = content.get('agent_name', 'Agent')
                text = content.get('text', '')
                agent_messages.append(f"**{agent_name}**: {text}\n")
        
        conversation_text = "\n".join(agent_messages)
        
        participant_list = ", ".join([f"@{name}" for name in participant_names])
        outcomes_text = "\n".join([f"- {outcome}" for outcome in desired_outcomes]) if desired_outcomes else "- Reach a clear decision"
        
        # Get current date/time for temporal context
        current_datetime = datetime.now(timezone.utc)
        current_date_str = current_datetime.strftime("%A, %B %d, %Y")
        current_time_str = current_datetime.strftime("%I:%M %p UTC")
        
        prompt = f"""You are the Ultimate Host providing the final conclusion for this debate.

📅 **Current Date & Time**: {current_date_str} at {current_time_str}

**Meeting Title**: {title}

**Participants**: {participant_list}

**Desired Outcomes**:
{outcomes_text}

**Full Debate Transcript**:
{conversation_text}

---

**Your Task**:
Provide your final conclusion as the Ultimate Host. Remember:
1. Consider the current date ({current_date_str}) when evaluating the recency and relevance of discussed information
2. Summarize the main positions discussed
3. Identify areas of consensus
4. Explain the majority viewpoint
5. Acknowledge dissenting opinions respectfully
6. Make a clear recommendation based on the discussion
7. Reference specific arguments from participants
8. Note if any information discussed appears outdated given today's date
9. Be objective and transparent about your reasoning

Provide your conclusion now:"""
        
        return prompt
