"""
WebSocket Service - Production Debate Room Transport
Handles authenticated WS connections, command processing, and event broadcast.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from .database import get_db_connection, get_cursor
from .debate_service import DebateService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per debate room with workspace isolation."""
    
    def __init__(self):
        # debate_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, debate_id: str, user_id: str, workspace_id: str):
        """Register a new WebSocket connection for a debate room."""
        await websocket.accept()
        
        if debate_id not in self.active_connections:
            self.active_connections[debate_id] = set()
        
        self.active_connections[debate_id].add(websocket)
        self.connection_metadata[websocket] = {
            'debate_id': debate_id,
            'user_id': user_id,
            'workspace_id': workspace_id,
            'connected_at': datetime.now(timezone.utc)
        }
        
        logger.info(f"WS connected: debate={debate_id}, user={user_id}, total={len(self.active_connections[debate_id])}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            debate_id = metadata['debate_id']
            
            if debate_id in self.active_connections:
                self.active_connections[debate_id].discard(websocket)
                if not self.active_connections[debate_id]:
                    del self.active_connections[debate_id]
            
            del self.connection_metadata[websocket]
            logger.info(f"WS disconnected: debate={debate_id}")
    
    async def broadcast_to_debate(self, debate_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections in a debate room."""
        if debate_id not in self.active_connections:
            return
        
        disconnected = []
        for websocket in self.active_connections[debate_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to websocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)
    
    async def send_to_client(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send to client: {e}")
            self.disconnect(websocket)


class WebSocketService:
    """Core WebSocket service for debate room realtime transport."""
    
    def __init__(self):
        self.manager = ConnectionManager()
        self.debate_service = DebateService()
    
    def _create_event_envelope(
        self,
        event_type: str,
        debate_id: str,
        payload: Dict[str, Any],
        sequence_number: Optional[int] = None,
        event_id: Optional[str] = None,
        sender_type: str = 'system',
        sender_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a strict event envelope for WebSocket messages."""
        return {
            'type': event_type,
            'debate_id': debate_id,
            'sequence_number': sequence_number,
            'event_id': event_id,
            'occurred_at': datetime.now(timezone.utc).isoformat(),
            'sender_type': sender_type,
            'sender_id': sender_id,
            'payload': payload,
            'request_id': request_id
        }
    
    def _create_ack(self, request_id: str, command: str) -> Dict[str, Any]:
        """Create ACK message for successful command."""
        return {
            'type': 'ack',
            'request_id': request_id,
            'command': command,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _create_error(self, request_id: str, command: str, error: str) -> Dict[str, Any]:
        """Create ERROR message for failed command."""
        return {
            'type': 'error',
            'request_id': request_id,
            'command': command,
            'error': error,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _persist_event(self, debate_id: str, event_type: str, payload: Dict[str, Any], sender_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Persist event to database and return with sequence_number."""
        try:
            with get_db_connection() as conn:
                cursor = get_cursor(conn)
                
                # Get next sequence number for this debate
                cursor.execute("""
                    SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
                    FROM events
                    WHERE debate_id = %s
                """, (debate_id,))
                
                result = cursor.fetchone()
                next_seq = result['next_seq'] if result else 1
                
                # Insert event
                cursor.execute("""
                    INSERT INTO events (
                        event_id, debate_id, event_type, sequence_number,
                        created_at, content, sender_id
                    ) VALUES (
                        gen_random_uuid(), %s, %s, %s,
                        NOW(), %s, %s
                    )
                    RETURNING event_id, sequence_number, created_at
                """, (debate_id, event_type, next_seq, json.dumps(payload), sender_id))
                
                event = cursor.fetchone()
                conn.commit()
                
                return {
                    'event_id': event['event_id'],
                    'sequence_number': event['sequence_number'],
                    'created_at': event['created_at'].isoformat()
                }
        except Exception as e:
            logger.error(f"Failed to persist event: {e}")
            return None
    
    async def handle_command(self, websocket: WebSocket, message: Dict[str, Any]):
        """Process command messages from client."""
        command = message.get('command')
        request_id = message.get('request_id', 'unknown')
        debate_id = message.get('debate_id')
        
        if not command or not debate_id:
            await self.manager.send_to_client(
                websocket,
                self._create_error(request_id, command or 'unknown', 'Missing command or debate_id')
            )
            return
        
        metadata = self.manager.connection_metadata.get(websocket, {})
        user_id = metadata.get('user_id')
        
        try:
            if command == 'join_presence':
                await self._handle_join_presence(websocket, debate_id, user_id, request_id)
            elif command == 'leave_presence':
                await self._handle_leave_presence(websocket, debate_id, user_id, request_id)
            elif command == 'typing':
                await self._handle_typing(websocket, debate_id, user_id, request_id, message.get('payload', {}))
            elif command == 'control.next_turn':
                await self._handle_next_turn(websocket, debate_id, user_id, request_id, message.get('payload', {}))
            elif command == 'control.pause':
                await self._handle_pause(websocket, debate_id, user_id, request_id)
            elif command == 'control.resume':
                await self._handle_resume(websocket, debate_id, user_id, request_id)
            elif command == 'control.end':
                await self._handle_end(websocket, debate_id, user_id, request_id)
            elif command == 'intervene':
                await self._handle_intervene(websocket, debate_id, user_id, request_id, message.get('payload', {}))
            else:
                await self.manager.send_to_client(
                    websocket,
                    self._create_error(request_id, command, f'Unknown command: {command}')
                )
        except Exception as e:
            logger.error(f"Command handler error: {e}")
            await self.manager.send_to_client(
                websocket,
                self._create_error(request_id, command, str(e))
            )
    
    async def _handle_join_presence(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str):
        """Handle join_presence command."""
        event_data = await self._persist_event(debate_id, 'presence_update', {
            'action': 'join',
            'participant_id': user_id
        }, sender_id=user_id)
        
        if event_data:
            # Broadcast to room
            envelope = self._create_event_envelope(
                'presence_update',
                debate_id,
                {'action': 'join', 'participant_id': user_id},
                sequence_number=event_data['sequence_number'],
                event_id=event_data['event_id'],
                sender_type='user',
                sender_id=user_id
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
        
        # Send ACK
        await self.manager.send_to_client(websocket, self._create_ack(request_id, 'join_presence'))
    
    async def _handle_leave_presence(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str):
        """Handle leave_presence command."""
        event_data = await self._persist_event(debate_id, 'presence_update', {
            'action': 'leave',
            'participant_id': user_id
        }, sender_id=user_id)
        
        if event_data:
            envelope = self._create_event_envelope(
                'presence_update',
                debate_id,
                {'action': 'leave', 'participant_id': user_id},
                sequence_number=event_data['sequence_number'],
                event_id=event_data['event_id'],
                sender_type='user',
                sender_id=user_id
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
        
        await self.manager.send_to_client(websocket, self._create_ack(request_id, 'leave_presence'))
    
    async def _handle_typing(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, payload: Dict):
        """Handle typing command (ephemeral, no persistence)."""
        envelope = self._create_event_envelope(
            'typing',
            debate_id,
            {'participant_id': user_id, **payload},
            sender_type='user',
            sender_id=user_id
        )
        await self.manager.broadcast_to_debate(debate_id, envelope)
        await self.manager.send_to_client(websocket, self._create_ack(request_id, 'typing'))
    
    async def _handle_next_turn(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, payload: Dict):
        """Handle control.next_turn command."""
        try:
            # Get OpenRouter key from payload (required for BYOK)
            openrouter_key = payload.get('openrouter_key')
            if not openrouter_key:
                raise ValueError("OpenRouter API key required for next turn")
            
            from .turn_orchestrator import TurnOrchestrator
            
            orchestrator = TurnOrchestrator(openrouter_key)
            result = orchestrator.trigger_next_turn(debate_id)
            
            # Broadcast the new agent message event to all clients
            event_data = await self._persist_event(debate_id, 'agent_message', {
                'agent_name': result['participant_name'],
                'message': result['message'],
                'turn_number': result['turn_number']
            }, sender_id=result['participant_id'])
            
            if event_data:
                envelope = self._create_event_envelope(
                    'agent_message',
                    debate_id,
                    {
                        'agent_name': result['participant_name'],
                        'message': result['message'],
                        'turn_number': result['turn_number']
                    },
                    sequence_number=event_data['sequence_number'],
                    event_id=event_data['event_id'],
                    sender_type='agent',
                    sender_id=result['participant_id']
                )
                await self.manager.broadcast_to_debate(debate_id, envelope)
            
            await self.manager.send_to_client(websocket, self._create_ack(request_id, 'control.next_turn'))
        except Exception as e:
            await self.manager.send_to_client(websocket, self._create_error(request_id, 'control.next_turn', str(e)))
    
    async def _handle_pause(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str):
        """Handle control.pause command."""
        debate = self.debate_service.pause_debate(debate_id)
        if debate:
            await self.manager.send_to_client(websocket, self._create_ack(request_id, 'control.pause'))
            # Broadcast state change
            envelope = self._create_event_envelope(
                'state_update',
                debate_id,
                {'state': 'paused'},
                sender_type='system'
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
        else:
            await self.manager.send_to_client(websocket, self._create_error(request_id, 'control.pause', 'Failed to pause'))
    
    async def _handle_resume(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str):
        """Handle control.resume command."""
        debate = self.debate_service.resume_debate(debate_id)
        if debate:
            await self.manager.send_to_client(websocket, self._create_ack(request_id, 'control.resume'))
            envelope = self._create_event_envelope(
                'state_update',
                debate_id,
                {'state': 'running'},
                sender_type='system'
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
        else:
            await self.manager.send_to_client(websocket, self._create_error(request_id, 'control.resume', 'Failed to resume'))
    
    async def _handle_end(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str):
        """Handle control.end command."""
        debate = self.debate_service.end_debate(debate_id)
        if debate:
            await self.manager.send_to_client(websocket, self._create_ack(request_id, 'control.end'))
            envelope = self._create_event_envelope(
                'state_update',
                debate_id,
                {'state': 'ended'},
                sender_type='system'
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
        else:
            await self.manager.send_to_client(websocket, self._create_error(request_id, 'control.end', 'Failed to end'))
    
    async def _handle_intervene(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, payload: Dict):
        """Handle intervene command."""
        try:
            message_text = payload.get('message')
            if not message_text:
                raise ValueError("Intervention message required")
            
            # Persist intervention as event
            event_data = await self._persist_event(debate_id, 'intervention', {
                'actor': payload.get('actor', 'Moderator'),
                'message': message_text
            }, sender_id=user_id)
            
            if event_data:
                envelope = self._create_event_envelope(
                    'intervention',
                    debate_id,
                    {
                        'actor': payload.get('actor', 'Moderator'),
                        'message': message_text
                    },
                    sequence_number=event_data['sequence_number'],
                    event_id=event_data['event_id'],
                    sender_type='user',
                    sender_id=user_id
                )
                await self.manager.broadcast_to_debate(debate_id, envelope)
            
            await self.manager.send_to_client(websocket, self._create_ack(request_id, 'intervene'))
        except Exception as e:
            await self.manager.send_to_client(websocket, self._create_error(request_id, 'intervene', str(e)))
    
    async def send_historical_events(self, websocket: WebSocket, debate_id: str, since_sequence: int = 0):
        """Send historical events to a newly connected client."""
        try:
            with get_db_connection() as conn:
                cursor = get_cursor(conn)
                cursor.execute("""
                    SELECT event_id, event_type, sequence_number, created_at, content, sender_id
                    FROM events
                    WHERE debate_id = %s AND sequence_number > %s
                    ORDER BY sequence_number ASC
                    LIMIT 100
                """, (debate_id, since_sequence))
                
                events = cursor.fetchall()
                
                for event in events:
                    try:
                        payload = json.loads(event['content']) if isinstance(event['content'], str) else event['content']
                    except:
                        payload = {}
                    
                    envelope = self._create_event_envelope(
                        event['event_type'],
                        debate_id,
                        payload,
                        sequence_number=event['sequence_number'],
                        event_id=event['event_id'],
                        sender_type='system' if not event.get('sender_id') else 'user',
                        sender_id=event.get('sender_id')
                    )
                    await self.manager.send_to_client(websocket, envelope)
        except Exception as e:
            logger.error(f"Failed to send historical events: {e}")


# Global manager instance
ws_service = WebSocketService()
