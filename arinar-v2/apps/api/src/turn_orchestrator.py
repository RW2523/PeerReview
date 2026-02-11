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
            
            # Build prompt
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({
                "role": "system",
                "content": f"Debate Topic: {debate['title'] or 'Untitled Debate'}\nProblem: {debate['description'] or 'No description'}"
            })
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Add turn instruction
            messages.append({
                "role": "user",
                "content": f"You are {agent_name}. It's your turn to contribute to the discussion. Share your perspective, insights, or respond to previous points. Keep it concise (2-3 paragraphs)."
            })
            
            # Call OpenRouter
            response = self.openrouter_client.chat_completion(
                model=model_id,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            agent_message = response['content']
            
            # Get next sequence number
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
