"""Turn-based debate orchestration for M2+"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import psycopg2.extras
from .database import get_db_connection, get_cursor
from .openrouter_client import OpenRouterClient


class TurnOrchestrator:
    """
    Manages turn-based agent participation in debates
    
    Features:
    - Round-robin turn order based on participant creation order
    - Tracks current turn index in debate metadata
    - Fetches prep packs for context
    - Generates and persists agent messages as events
    """
    
    def __init__(self, openrouter_api_key: str):
        self.openrouter_client = OpenRouterClient(openrouter_api_key)
    
    def trigger_next_turn(self, debate_id: str) -> Dict[str, Any]:
        """
        Execute the next agent's turn in the debate
        
        Returns:
            Dict with event_id, participant_id, participant_name, message, turn_number
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
                raise ValueError(f"Debate must be in 'running' state, current state: {debate['state']}")
            
            # Get participants in turn order (by creation time)
            cursor.execute("""
                SELECT participant_id, participant_type, role_name, agent_config, created_at
                FROM participants
                WHERE debate_id = %s
                ORDER BY created_at ASC
            """, (debate_id,))
            
            participants = cursor.fetchall()
            if not participants:
                raise ValueError(f"No participants found for debate {debate_id}")
            
            # Get current turn index from policy_config
            policy_config = debate['policy_config'] or {}
            current_turn_index = policy_config.get('current_turn_index', 0)
            total_turns = policy_config.get('total_turns_taken', 0)
            
            # Determine next participant (round-robin)
            next_participant_idx = current_turn_index % len(participants)
            next_participant = participants[next_participant_idx]
            
            # Get debate history for context
            cursor.execute("""
                SELECT event_type, sender_type, sender_id, content, sequence_number, created_at
                FROM events
                WHERE debate_id = %s
                ORDER BY sequence_number ASC
                LIMIT 50
            """, (debate_id,))
            
            history_events = cursor.fetchall()
            conversation_history = self._build_conversation_history(
                debate['title'],
                debate['description'],
                history_events
            )
            
            # Get agent config
            agent_config = next_participant['agent_config'] or {}
            agent_name = agent_config.get('name') or next_participant['role_name']
            model_id = agent_config.get('model_id', 'openai/gpt-4o-mini')
            system_prompt = agent_config.get('system_prompt', '')
            
            # Get prep pack for this agent
            cursor.execute("""
                SELECT content, metadata
                FROM agent_knowledge_units
                WHERE agent_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (next_participant['participant_id'],))
            
            prep_pack_row = cursor.fetchone()
            prep_pack = prep_pack_row['content'] if prep_pack_row else None
            
            # Get agenda and desired outcomes
            agenda = policy_config.get('agenda', [])
            desired_outcomes = policy_config.get('desired_outcomes', [])
            
            # Build prompt
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Context message with topic, agenda, outcomes
            context_parts = [f"Debate Topic: {debate['title'] or 'Untitled Debate'}"]
            if debate['description']:
                context_parts.append(f"Problem: {debate['description']}")
            if agenda:
                context_parts.append(f"Agenda:\n" + "\n".join(f"  - {item}" for item in agenda))
            if desired_outcomes:
                context_parts.append(f"Desired Outcomes:\n" + "\n".join(f"  - {item}" for item in desired_outcomes))
            
            messages.append({
                "role": "system",
                "content": "\n\n".join(context_parts)
            })
            
            # Add prep pack if available and valid
            if prep_pack and not prep_pack.startswith("Error"):
                messages.append({
                    "role": "system",
                    "content": f"Your preparation notes:\n{prep_pack}"
                })
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Build list of other participants for @mentions
            other_participants = [
                p['agent_config'].get('name', p['role_name']) 
                for p in participants 
                if p['participant_id'] != next_participant['participant_id']
            ]
            participant_list = ", ".join([f"@{name}" for name in other_participants])
            
            # Calculate progress and urgency
            max_rounds = policy_config.get('max_rounds')
            timebox_minutes = policy_config.get('timebox_minutes')
            current_round = (total_turns // len(participants)) + 1
            turn_in_round = (total_turns % len(participants)) + 1
            
            # Determine urgency level and response length
            if max_rounds:
                rounds_remaining = max_rounds - current_round + 1
                progress_pct = (current_round / max_rounds) * 100
                
                if rounds_remaining <= 1:
                    urgency = "FINAL ROUND"
                    length_instruction = "Keep it VERY brief (2-3 sentences). Focus on your final recommendation or key takeaway."
                elif rounds_remaining <= 2:
                    urgency = f"Only {rounds_remaining} rounds left"
                    length_instruction = "Keep it concise (3-4 sentences). Be direct and actionable."
                else:
                    urgency = f"Round {current_round}/{max_rounds}"
                    length_instruction = "Keep it short and crisp (4-5 sentences). Only expand into a paragraph if making a critical point."
            else:
                urgency = f"Turn {total_turns + 1}"
                length_instruction = "Keep it short and crisp (4-5 sentences). Only expand into a paragraph if making a critical point."
            
            # Add turn instruction with conversational guidance
            role_context = agent_config.get('description', f"You are {agent_name}")
            
            conversational_instruction = f"""{role_context}

**Context:** {urgency} | Turn {turn_in_round}/{len(participants)} in this round
**Other Participants:** {participant_list}

**Your Response:**
{length_instruction}

**Communication Style:**
- Use @mentions to directly address others
- Explicitly agree/disagree with specific points
- Ask questions to invite responses
- Reference what others said
- Be authentic and human-like"""
            
            messages.append({
                "role": "user",
                "content": conversational_instruction
            })
            
            # Call OpenRouter
            response = self.openrouter_client.chat_completion(
                model=model_id,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            agent_message = response['content']
            
            # Get next sequence number (scoped to this debate)
            cursor.execute("""
                SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
                FROM events
                WHERE debate_id = %s
            """, (debate_id,))
            
            next_seq = cursor.fetchone()['next_seq']
            
            # Persist event
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO events (
                    event_id, debate_id, event_type, sender_type, sender_id,
                    sequence_number, content, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                debate_id,
                'agent_message',
                'agent',
                next_participant['participant_id'],
                next_seq,
                psycopg2.extras.Json({
                    'agent_name': agent_name,
                    'text': agent_message,
                    'model': response.get('model', model_id),
                    'turn': total_turns + 1,
                    'turn_index': current_turn_index
                }),
                datetime.now(timezone.utc)
            ))
            
            # Update turn index in policy_config
            policy_config['current_turn_index'] = current_turn_index + 1
            policy_config['total_turns_taken'] = total_turns + 1
            policy_config['last_participant_id'] = next_participant['participant_id']
            
            cursor.execute("""
                UPDATE debates
                SET policy_config = %s, updated_at = %s
                WHERE debate_id = %s
            """, (
                psycopg2.extras.Json(policy_config),
                datetime.now(timezone.utc),
                debate_id
            ))
            
            conn.commit()
            
            return {
                'event_id': event_id,
                'participant_id': next_participant['participant_id'],
                'participant_name': agent_name,
                'message': agent_message,
                'turn_number': total_turns + 1,
                'sequence_number': next_seq
            }
    
    def _build_conversation_history(
        self,
        title: Optional[str],
        description: Optional[str],
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Build conversation history from events"""
        history = []
        
        for event in events:
            content = event.get('content') or {}
            
            if event['event_type'] == 'agent_message':
                agent_name = content.get('agent_name', 'Agent')
                text = content.get('text', '')
                history.append({
                    "role": "assistant",
                    "content": f"{agent_name}: {text}"
                })
            elif event['event_type'] == 'human_message':
                text = content.get('text', '')
                history.append({
                    "role": "user",
                    "content": text
                })
        
        # Limit history to last 10 messages to avoid context overflow
        return history[-10:]
