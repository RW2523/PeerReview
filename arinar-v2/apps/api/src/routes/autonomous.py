"""
Autonomous Debate API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..autonomous_debate_service import autonomous_service

router = APIRouter(prefix="/api/debates", tags=["autonomous"])


class StartAutonomousRequest(BaseModel):
    auto_turn_delay_seconds: int = 10


@router.post("/{debate_id}/start-autonomous")
async def start_autonomous(
    debate_id: str,
    request: StartAutonomousRequest
):
    """Start autonomous YOLO debate"""
    
    # Get API key from user or environment
    api_key = user.get('openrouter_api_key') if user else None
    if not api_key:
        import os
        api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        raise HTTPException(400, "OpenRouter API key required")
    
    result = await autonomous_service.start_autonomous_debate(
        debate_id=debate_id,
        openrouter_api_key=api_key,
        auto_turn_delay=request.auto_turn_delay_seconds
    )
    
    return result


@router.post("/{debate_id}/pause-autonomous")
async def pause_autonomous(debate_id: str):
    """Pause autonomous debate"""
    await autonomous_service.pause_autonomous_debate(debate_id)
    return {"status": "paused"}


@router.post("/{debate_id}/resume-autonomous")
async def resume_autonomous(debate_id: str):
    """Resume autonomous debate"""
    await autonomous_service.resume_autonomous_debate(debate_id)
    return {"status": "resumed"}


@router.get("/{debate_id}/autonomous-status")
async def get_autonomous_status(debate_id: str):
    """Get autonomous debate status"""
    status = autonomous_service._get_debate_status(debate_id)
    is_running = debate_id in autonomous_service.running_debates
    
    return {
        "status": status,
        "is_running": is_running,
        "has_background_task": is_running
    }
