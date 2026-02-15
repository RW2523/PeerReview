"""
WebSocket Command Handlers
Extracted from websocket_service.py to maintain file size compliance.
"""
import logging
from typing import Dict, Any
from fastapi import WebSocket
from .database import get_db_connection, get_cursor
from .debate_service import DebateService

logger = logging.getLogger(__name__)


class WebSocketCommandHandlers:
    """Command handlers for WebSocket debate room operations."""
    
    def __init__(self, manager, debate_service: DebateService):
        self.manager = manager
        self.debate_service = debate_service
    
    async def handle_join_presence(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, persist_event_fn, create_envelope_fn, create_ack_fn):
        """Handle join_presence command."""
        event_data = await persist_event_fn(debate_id, 'presence_update', {
            'action': 'join',
            'participant_id': user_id
        }, sender_id=user_id)
        
        if event_data:
            envelope = create_envelope_fn(
                'presence_update',
                debate_id,
                {'action': 'join', 'participant_id': user_id},
                sequence_number=event_data['sequence_number'],
                event_id=event_data['event_id'],
                sender_type='user',
                sender_id=user_id
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
        
        await self.manager.send_to_client(websocket, create_ack_fn(request_id, 'join_presence'))
    
    async def handle_leave_presence(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, persist_event_fn, create_envelope_fn, create_ack_fn):
        """Handle leave_presence command."""
        event_data = await persist_event_fn(debate_id, 'presence_update', {
            'action': 'leave',
            'participant_id': user_id
        }, sender_id=user_id)
        
        if event_data:
            envelope = create_envelope_fn(
                'presence_update',
                debate_id,
                {'action': 'leave', 'participant_id': user_id},
                sequence_number=event_data['sequence_number'],
                event_id=event_data['event_id'],
                sender_type='user',
                sender_id=user_id
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
        
        await self.manager.send_to_client(websocket, create_ack_fn(request_id, 'leave_presence'))
    
    async def handle_typing(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, payload: Dict, create_envelope_fn, create_ack_fn):
        """Handle typing command (ephemeral, not persisted)."""
        # Don't persist typing events (they're ephemeral)
        envelope = create_envelope_fn(
            'typing',
            debate_id,
            {'participant_id': user_id, 'ping': payload.get('ping', False)},
            sender_type='user',
            sender_id=user_id
        )
        await self.manager.broadcast_to_debate(debate_id, envelope)
        await self.manager.send_to_client(websocket, create_ack_fn(request_id, 'typing'))
    
    async def handle_next_turn(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, payload: Dict, create_envelope_fn, create_ack_fn, create_error_fn):
        """Handle control.next_turn command."""
        print(f"\n🎮 WEBSOCKET COMMAND: control.next_turn received")
        print(f"   Debate ID: {debate_id}")
        print(f"   User ID: {user_id}")
        print(f"   Request ID: {request_id}")
        print(f"   Payload keys: {list(payload.keys())}\n")
        
        try:
            # Get OpenRouter key from payload (required for BYOK)
            openrouter_key = payload.get('openrouter_key')
            if not openrouter_key:
                print("❌ ERROR: No OpenRouter key in payload!")
                raise ValueError("OpenRouter API key required for next turn")
            
            print(f"✅ OpenRouter key found, triggering turn orchestrator...")
            from .turn_orchestrator import TurnOrchestrator
            
            # TurnOrchestrator.trigger_next_turn persists the event and returns event details
            orchestrator = TurnOrchestrator(openrouter_key)
            result = orchestrator.trigger_next_turn(debate_id)
            print(f"✅ Turn orchestrator returned successfully!")
            
            # Broadcast using the ALREADY PERSISTED event (no duplicate insert)
            envelope = create_envelope_fn(
                'agent_message',
                debate_id,
                {
                    'agent_name': result['participant_name'],
                    'message': result['message'],
                    'turn_number': result['turn_number']
                },
                sequence_number=result['sequence_number'],
                event_id=result['event_id'],
                sender_type='agent',
                sender_id=result['participant_id']
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
            
            print(f"✅ Broadcasting complete, sending ACK to client\n")
            await self.manager.send_to_client(websocket, create_ack_fn(request_id, 'control.next_turn'))
        except Exception as e:
            print(f"❌ WEBSOCKET ERROR in handle_next_turn: {e}")
            import traceback
            traceback.print_exc()
            await self.manager.send_to_client(websocket, create_error_fn(request_id, 'control.next_turn', str(e)))
    
    async def handle_pause(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, create_envelope_fn, create_ack_fn, create_error_fn):
        """Handle control.pause command."""
        debate = self.debate_service.pause_debate(debate_id)
        if debate:
            await self.manager.send_to_client(websocket, create_ack_fn(request_id, 'control.pause'))
            envelope = create_envelope_fn(
                'state_update',
                debate_id,
                {'state': 'paused'},
                sender_type='system'
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
        else:
            await self.manager.send_to_client(websocket, create_error_fn(request_id, 'control.pause', 'Failed to pause'))
    
    async def handle_resume(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, create_envelope_fn, create_ack_fn, create_error_fn):
        """Handle control.resume command."""
        debate = self.debate_service.resume_debate(debate_id)
        if debate:
            await self.manager.send_to_client(websocket, create_ack_fn(request_id, 'control.resume'))
            envelope = create_envelope_fn(
                'state_update',
                debate_id,
                {'state': 'running'},
                sender_type='system'
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
        else:
            await self.manager.send_to_client(websocket, create_error_fn(request_id, 'control.resume', 'Failed to resume'))
    
    async def handle_end(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, create_envelope_fn, create_ack_fn, create_error_fn):
        """Handle control.end command."""
        debate = self.debate_service.end_debate(debate_id)
        if debate:
            await self.manager.send_to_client(websocket, create_ack_fn(request_id, 'control.end'))
            envelope = create_envelope_fn(
                'state_update',
                debate_id,
                {'state': 'ended'},
                sender_type='system'
            )
            await self.manager.broadcast_to_debate(debate_id, envelope)
        else:
            await self.manager.send_to_client(websocket, create_error_fn(request_id, 'control.end', 'Failed to end'))
    
    async def handle_intervene(self, websocket: WebSocket, debate_id: str, user_id: str, request_id: str, payload: Dict, persist_event_fn, create_envelope_fn, create_ack_fn, create_error_fn):
        """Handle intervene command."""
        print(f"\n🎙️ INTERVENTION RECEIVED:")
        print(f"   Debate ID: {debate_id}")
        print(f"   User ID: {user_id}")
        print(f"   Message: {payload.get('message', '')[:100]}")
        print(f"   Tagged agents: {payload.get('tagged_agents', [])}\n")
        
        try:
            message_text = payload.get('message')
            if not message_text:
                raise ValueError("Intervention message required")
            
            # Persist intervention as 'human_message' event type (to match turn_orchestrator expectations)
            event_data = await persist_event_fn(debate_id, 'human_message', {
                'actor': payload.get('actor', 'Moderator'),
                'text': message_text,  # Changed from 'message' to 'text' to match turn_orchestrator
                'tagged_agents': payload.get('tagged_agents', []),
                'action': 'intervene'
            }, sender_id=user_id)
            
            print(f"✅ Intervention persisted as human_message with event_id: {event_data.get('event_id') if event_data else 'FAILED'}\n")
            
            if event_data:
                # Broadcast as 'human_message' type for consistency
                envelope = create_envelope_fn(
                    'human_message',
                    debate_id,
                    {
                        'actor': payload.get('actor', 'Moderator'),
                        'text': message_text,
                        'tagged_agents': payload.get('tagged_agents', [])
                    },
                    sequence_number=event_data['sequence_number'],
                    event_id=event_data['event_id'],
                    sender_type='user',
                    sender_id=user_id
                )
                await self.manager.broadcast_to_debate(debate_id, envelope)
                print(f"✅ Intervention broadcasted to all debate participants\n")
            
            await self.manager.send_to_client(websocket, create_ack_fn(request_id, 'intervene'))
        except Exception as e:
            print(f"❌ ERROR handling intervention: {e}")
            import traceback
            traceback.print_exc()
            await self.manager.send_to_client(websocket, create_error_fn(request_id, 'intervene', str(e)))
