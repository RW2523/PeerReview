"""Debate lifecycle service for M2 control operations"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import psycopg2.extras
from .database import get_db_connection, get_cursor
from .state_machine import DebateState, DebateStateMachine, StateTransitionError


class DebateService:
    """
    Service for debate lifecycle operations (M2)
    
    Handles: start, pause, resume, intervene, end
    """
    
    def get_debate(self, debate_id: str) -> Optional[Dict[str, Any]]:
        """Get debate by ID"""
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute("""
                SELECT debate_id, workspace_id, title, description, state, 
                       policy_config, created_at, updated_at
                FROM debates
                WHERE debate_id = %s
            """, (debate_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_debate(
        self,
        workspace_id: str,
        title: str,
        policy_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create new debate in pending state"""
        debate_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        policy_json = psycopg2.extras.Json(policy_config or {})
        
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute("""
                INSERT INTO debates (
                    debate_id, workspace_id, title, state, policy_config,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING debate_id, workspace_id, title, state, created_at
            """, (
                debate_id,
                workspace_id,
                title,
                DebateState.PENDING.value,
                policy_json,
                now,
                now
            ))
            
            row = cursor.fetchone()
            return dict(row)
    
    def start_debate(self, debate_id: str) -> Dict[str, Any]:
        """Start debate (pending -> running)"""
        debate = self.get_debate(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")
        
        current_state = DebateState(debate['state'])
        
        if not DebateStateMachine.can_start(current_state):
            raise StateTransitionError(
                f"Cannot start debate in {current_state.value} state"
            )
        
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            # Update debate state
            cursor.execute("""
                UPDATE debates
                SET state = %s, updated_at = %s
                WHERE debate_id = %s
            """, (DebateState.RUNNING.value, datetime.now(timezone.utc), debate_id))
            
            # Create system event
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO events (
                    event_id, debate_id, event_type, sender_type,
                    sequence_number, content, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                debate_id,
                'system_message',
                'system',
                self._get_next_sequence(cursor, debate_id),
                psycopg2.extras.Json({'text': 'Debate started', 'action': 'start'}),
                datetime.now(timezone.utc)
            ))
        
        return self.get_debate(debate_id)
    
    def pause_debate(self, debate_id: str) -> Dict[str, Any]:
        """Pause debate (running -> paused)"""
        debate = self.get_debate(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")
        
        current_state = DebateState(debate['state'])
        
        if not DebateStateMachine.can_pause(current_state):
            raise StateTransitionError(
                f"Cannot pause debate in {current_state.value} state"
            )
        
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            cursor.execute("""
                UPDATE debates
                SET state = %s, updated_at = %s
                WHERE debate_id = %s
            """, (DebateState.PAUSED.value, datetime.now(timezone.utc), debate_id))
            
            # Create system event
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO events (
                    event_id, debate_id, event_type, sender_type,
                    sequence_number, content, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                debate_id,
                'system_message',
                'system',
                self._get_next_sequence(cursor, debate_id),
                psycopg2.extras.Json({'text': 'Debate paused', 'action': 'pause'}),
                datetime.now(timezone.utc)
            ))
        
        return self.get_debate(debate_id)
    
    def resume_debate(self, debate_id: str) -> Dict[str, Any]:
        """Resume debate (paused -> running)"""
        debate = self.get_debate(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")
        
        current_state = DebateState(debate['state'])
        
        if not DebateStateMachine.can_resume(current_state):
            raise StateTransitionError(
                f"Cannot resume debate in {current_state.value} state"
            )
        
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            cursor.execute("""
                UPDATE debates
                SET state = %s, updated_at = %s
                WHERE debate_id = %s
            """, (DebateState.RUNNING.value, datetime.now(timezone.utc), debate_id))
            
            # Create system event
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO events (
                    event_id, debate_id, event_type, sender_type,
                    sequence_number, content, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                debate_id,
                'system_message',
                'system',
                self._get_next_sequence(cursor, debate_id),
                psycopg2.extras.Json({'text': 'Debate resumed', 'action': 'resume'}),
                datetime.now(timezone.utc)
            ))
        
        return self.get_debate(debate_id)
    
    def intervene(
        self,
        debate_id: str,
        message: str,
        tagged_agents: Optional[list] = None
    ) -> Dict[str, Any]:
        """Add intervention to debate"""
        debate = self.get_debate(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")
        
        current_state = DebateState(debate['state'])
        
        if not DebateStateMachine.can_intervene(current_state):
            raise StateTransitionError(
                f"Cannot intervene in debate in {current_state.value} state"
            )
        
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            # Create intervention event
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO events (
                    event_id, debate_id, event_type, sender_type,
                    sequence_number, content, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                debate_id,
                'intervention',
                'human',
                self._get_next_sequence(cursor, debate_id),
                psycopg2.extras.Json({
                    'text': message,
                    'tagged_agents': tagged_agents or [],
                    'action': 'intervene'
                }),
                datetime.now(timezone.utc)
            ))
        
        return {
            'event_id': event_id,
            'debate_id': debate_id,
            'message': message,
            'tagged_agents': tagged_agents or []
        }
    
    def end_debate(self, debate_id: str) -> Dict[str, Any]:
        """End debate (running/paused -> ended)"""
        debate = self.get_debate(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")
        
        current_state = DebateState(debate['state'])
        
        if not DebateStateMachine.can_end(current_state):
            raise StateTransitionError(
                f"Cannot end debate in {current_state.value} state"
            )
        
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            cursor.execute("""
                UPDATE debates
                SET state = %s, updated_at = %s
                WHERE debate_id = %s
            """, (DebateState.ENDED.value, datetime.now(timezone.utc), debate_id))
            
            # Create system event
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO events (
                    event_id, debate_id, event_type, sender_type,
                    sequence_number, content, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                debate_id,
                'system_message',
                'system',
                self._get_next_sequence(cursor, debate_id),
                psycopg2.extras.Json({'text': 'Debate ended', 'action': 'end'}),
                datetime.now(timezone.utc)
            ))
        
        # TODO #TICKET-06: Generate summary/minutes/action_items (Phase 5)
        return self.get_debate(debate_id)
    
    def _get_next_sequence(self, cursor, debate_id: str) -> int:
        """Get next sequence number for debate events"""
        cursor.execute("""
            SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_seq
            FROM events
            WHERE debate_id = %s
        """, (debate_id,))
        
        result = cursor.fetchone()
        return result['next_seq'] if result else 1
