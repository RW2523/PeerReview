"""Turn orchestration endpoints"""
from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import Dict, Any
from ..auth import get_current_user, check_workspace_access
from ..debate_service import DebateService
from ..turn_orchestrator import TurnOrchestrator
from ..openrouter_client import OpenRouterAuthError

router = APIRouter()


@router.post("/debates/{debate_id}/turn/next")
async def trigger_next_turn(
    debate_id: str,
    x_openrouter_key: str = Header(..., alias="X-OpenRouter-Key"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Trigger the next agent to take their turn in the debate (M2+)
    
    Uses round-robin ordering based on participant creation order.
    Requires debate to be in 'running' state.
    
    Protected: Requires valid JWT and workspace access
    
    Headers:
        X-OpenRouter-Key: OpenRouter API key (BYOK)
    
    Returns:
        Event details for the generated agent message
    
    Raises:
        400: Invalid state or no participants
        401: Unauthorized
        403: Forbidden
        404: Debate not found
        500: Internal server error
    """
    service = DebateService()
    debate = service.get_debate(debate_id)
    
    if not debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debate {debate_id} not found"
        )
    
    check_workspace_access(current_user, debate['workspace_id'])
    
    try:
        orchestrator = TurnOrchestrator(x_openrouter_key)
        result = orchestrator.trigger_next_turn(debate_id)
        
        return {
            "event_id": result['event_id'],
            "participant_id": result['participant_id'],
            "participant_name": result['participant_name'],
            "message": result['message'],
            "turn_number": result['turn_number'],
            "sequence_number": result['sequence_number']
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except OpenRouterAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OpenRouter authentication failed: {str(e)}"
        )
    except Exception as e:
        import traceback
        error_detail = str(e)
        
        # Better error messages for common issues
        if "OpenRouter API error" in error_detail:
            if "502" in error_detail or "Clerk" in error_detail:
                error_detail = "OpenRouter API authentication failed. Please check your API key or try again later."
            elif "401" in error_detail or "authentication" in error_detail.lower():
                error_detail = "Invalid OpenRouter API key. Please update your API key in Settings."
        
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute turn: {error_detail}"
        )
