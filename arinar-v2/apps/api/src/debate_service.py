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
    
    def __init__(self):
        """Initialize and check if autonomous columns exist"""
        self._has_autonomous_cols = None
    
    def _check_autonomous_cols(self) -> bool:
        """Check if autonomous columns exist (cached)"""
        if self._has_autonomous_cols is not None:
            return self._has_autonomous_cols
        
        try:
            with get_db_connection() as conn:
                cursor = get_cursor(conn)
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'debates' 
                    AND column_name = 'autonomous_mode'
                """)
                self._has_autonomous_cols = cursor.fetchone() is not None
        except Exception:
            self._has_autonomous_cols = False
        
        return self._has_autonomous_cols
    
    def get_debate(self, debate_id: str) -> Optional[Dict[str, Any]]:
        """Get debate by ID - always include autonomous columns"""
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            # Always query autonomous columns (migration has been applied)
            cursor.execute("""
                SELECT debate_id, workspace_id, title, description, state, 
                       policy_config, created_at, updated_at, started_at, ended_at,
                       autonomous_mode, autonomous_status, auto_turn_delay_seconds
                FROM debates
                WHERE debate_id = %s
            """, (debate_id,))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                return result
            return None
    
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
    
    def update_policy_config(self, debate_id: str, policy_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update policy_config for a debate (e.g., extend rounds or time)"""
        debate = self.get_debate(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")
        
        # Merge updates with existing policy_config
        current_policy = debate.get('policy_config') or {}
        updated_policy = {**current_policy, **policy_updates}
        
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute("""
                UPDATE debates
                SET policy_config = %s, updated_at = NOW()
                WHERE debate_id = %s
                RETURNING debate_id, policy_config
            """, (
                psycopg2.extras.Json(updated_policy),
                debate_id
            ))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def start_debate(self, debate_id: str) -> Dict[str, Any]:
        """Start debate (pending -> running)"""
        debate = self.get_debate(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")
        
        current_state = DebateState(debate['state'])
        
        if not DebateStateMachine.can_start(current_state):
            if current_state == DebateState.RUNNING:
                raise StateTransitionError(
                    f"Debate is already running. Use pause/resume to control it."
                )
            elif current_state == DebateState.ENDED:
                raise StateTransitionError(
                    f"Debate has already ended. Create a new debate to start another."
                )
            else:
                raise StateTransitionError(
                    f"Cannot start debate in {current_state.value} state. Current state must be 'pending'."
                )
        
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            # Update debate state and record started_at timestamp
            now = datetime.now(timezone.utc)
            cursor.execute("""
                UPDATE debates
                SET state = %s, updated_at = %s, started_at = %s
                WHERE debate_id = %s
            """, (DebateState.RUNNING.value, now, now, debate_id))
            
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
            
            # Create intervention event (using 'human_message' type to match turn_orchestrator expectations)
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO events (
                    event_id, debate_id, event_type, sender_type,
                    sequence_number, content, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                debate_id,
                'human_message',  # Changed from 'intervention' to match turn_orchestrator
                'human',
                self._get_next_sequence(cursor, debate_id),
                psycopg2.extras.Json({
                    'text': message,
                    'tagged_agents': tagged_agents or [],
                    'actor': 'Moderator',  # Add actor field expected by turn_orchestrator
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
    
    def list_debates(
        self,
        workspace_id: str,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List debates in workspace with cursor pagination.
        
        Cursor is debate_id for simple pagination.
        Returns items + next_cursor (if more results exist).
        """
        with get_db_connection() as conn:
            db_cursor = get_cursor(conn)
            
            if cursor:
                # Fetch after cursor
                db_cursor.execute("""
                    SELECT debate_id, workspace_id, title, state,
                           created_at, updated_at, started_at, ended_at
                    FROM debates
                    WHERE workspace_id = %s AND debate_id > %s
                    ORDER BY debate_id ASC
                    LIMIT %s
                """, (workspace_id, cursor, limit + 1))
            else:
                # First page
                db_cursor.execute("""
                    SELECT debate_id, workspace_id, title, state,
                           created_at, updated_at, started_at, ended_at
                    FROM debates
                    WHERE workspace_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (workspace_id, limit + 1))
            
            rows = db_cursor.fetchall()
            items = [dict(row) for row in rows]
            
            # Check if there are more results
            next_cursor = None
            if len(items) > limit:
                items = items[:limit]
                next_cursor = items[-1]["debate_id"]
            
            return {
                "items": items,
                "next_cursor": next_cursor
            }
    
    def get_participants(self, debate_id: str):
        """Get all participants for a debate"""
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute("""
                SELECT participant_id, debate_id, participant_type, role_name, agent_config, created_at
                FROM participants
                WHERE debate_id = %s
                ORDER BY created_at ASC
            """, (debate_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
