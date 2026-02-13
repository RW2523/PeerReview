"""
WebSocket Routes - Authenticated Debate Room Transport
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict, Any
from ..auth import get_current_user_ws, check_workspace_access
from ..debate_service import DebateService
from ..websocket_service import ws_service
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/debates/{debate_id}")
async def websocket_debate_room(
    websocket: WebSocket,
    debate_id: str
):
    """
    WebSocket endpoint for debate room realtime transport.
    
    Auth: Validates Supabase JWT via query param `token`
    
    Features:
    - Historical event replay
    - Realtime event broadcast
    - Command processing (presence, typing, controls)
    - ACK/ERROR responses
    - Workspace isolation
    
    Message format (client → server):
    {
        "command": "join_presence" | "leave_presence" | "typing" | "control.*",
        "debate_id": "uuid",
        "request_id": "client-generated-id",
        "payload": {}
    }
    
    Message format (server → client):
    {
        "type": "event_type",
        "debate_id": "uuid",
        "sequence_number": 1,
        "event_id": "uuid",
        "occurred_at": "ISO8601",
        "sender_type": "system" | "user" | "agent",
        "sender_id": "uuid",
        "payload": {},
        "request_id": "optional"
    }
    
    ACK format:
    {
        "type": "ack",
        "request_id": "...",
        "command": "...",
        "timestamp": "ISO8601"
    }
    
    ERROR format:
    {
        "type": "error",
        "request_id": "...",
        "command": "...",
        "error": "error message",
        "timestamp": "ISO8601"
    }
    """
    # Extract token from query params
    query_params = dict(websocket.query_params)
    token = query_params.get('token')
    
    # Development mode: bypass auth if REQUIRE_AUTH=false
    if not settings.require_auth:
        logger.info(f"⚠️  Development mode: bypassing auth for WebSocket (REQUIRE_AUTH=false)")
        user = {
            'sub': '00000000-0000-0000-0000-000000000999',  # Valid UUID format for dev user
            'workspace_id': '00000000-0000-0000-0000-000000000101',
            'tenant_id': '00000000-0000-0000-0000-000000000001',
            'email': 'dev@arinar.ai',
            'role': 'operator'
        }
    else:
        # Production mode: validate token
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing auth token")
            return
        
        # Validate token and get user
        try:
            user = await get_current_user_ws(token)
        except HTTPException as e:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid auth token")
            return
    
    # Verify debate exists and user has workspace access
    debate_service = DebateService()
    debate = debate_service.get_debate(debate_id)
    
    if not debate:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Debate not found")
        return
    
    try:
        check_workspace_access(user, debate['workspace_id'])
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Access denied")
        return
    
    # Accept connection
    await ws_service.manager.connect(websocket, debate_id, user['sub'], debate['workspace_id'])
    
    try:
        # Send historical events
        since_sequence = int(query_params.get('since', 0))
        await ws_service.send_historical_events(websocket, debate_id, since_sequence)
        
        # Event loop - listen for commands
        while True:
            data = await websocket.receive_json()
            await ws_service.handle_command(websocket, data)
    
    except WebSocketDisconnect:
        ws_service.manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected: debate={debate_id}, user={user['sub']}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_service.manager.disconnect(websocket)
