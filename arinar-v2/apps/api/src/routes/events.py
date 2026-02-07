"""Events and SSE streaming endpoints"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from ..auth import get_current_user, check_workspace_access
from ..debate_service import DebateService
from ..stream_service import StreamService

router = APIRouter()


@router.get("/debates/{debate_id}/events/stream")
async def stream_debate_events(
    debate_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    since: Optional[int] = None
):
    """
    Stream debate events via Server-Sent Events (SSE)
    
    Protected: Requires valid JWT and workspace access
    
    Args:
        debate_id: Debate ID to stream
        since: Optional sequence number to resume from
    
    Returns:
        StreamingResponse with SSE events
    
    Event types:
        - debate_event: Individual event from debate
        - state_update: Debate state changed
        - stream_end: Stream terminated (debate ended)
        - error: Error occurred
    
    Raises:
        401: Unauthorized
        403: Forbidden (workspace access denied)
        404: Debate not found
    """
    # Verify debate exists and user has access
    service = DebateService()
    debate = service.get_debate(debate_id)
    
    if not debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debate {debate_id} not found"
        )
    
    check_workspace_access(current_user, debate['workspace_id'])
    
    # Stream events
    stream_service = StreamService()
    
    return StreamingResponse(
        stream_service.stream_debate_events(debate_id, since_sequence=since),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
