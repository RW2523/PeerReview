"""Debate-related endpoints"""
from fastapi import APIRouter, HTTPException, status, Depends, Query, Header
from typing import Dict, Any, Optional, List
from ..auth import get_current_user, check_workspace_access
from ..debate_engine import DebateEngine
from ..debate_service import DebateService
from ..summary_service import SummaryService
from ..meeting_setup_service import MeetingSetupService, MeetingSetupError
from ..openrouter_client import OpenRouterAuthError, OpenRouterError
from ..state_machine import StateTransitionError
from ..turn_orchestrator import TurnOrchestrator
from ..schemas.debates import (
    DebateRunRequest,
    DebateRunResponse,
    CreateDebateRequest,
    DebateResponse,
    InterveneRequest,
    InterventionResponse,
    DebateListResponse,
    DebateListItem,
)
from ..schemas.summary import (
    SummarizeRequest,
    SummaryResponse,
    ActionItem,
)
from ..schemas.setup import (
    DebateSetupRequest,
    DebateSetupResponse,
)

router = APIRouter()


@router.get("/debates", response_model=DebateListResponse)
async def list_debates(
    workspace_id: str = Query(..., description="Workspace ID to filter debates"),
    limit: int = Query(20, ge=1, le=100, description="Max debates to return"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    List debates in a workspace with cursor pagination.
    Protected by workspace access checks.
    """
    # Check workspace access
    if current_user:
        check_workspace_access(workspace_id, current_user)
    
    service = DebateService()
    
    try:
        # Get debates from DB
        debates_data = service.list_debates(workspace_id, limit=limit, cursor=cursor)
        
        items = [
            DebateListItem(
                debate_id=d["debate_id"],
                workspace_id=d["workspace_id"],
                title=d["title"],
                state=d["state"],
                created_at=d["created_at"],
                updated_at=d.get("updated_at"),
                started_at=d.get("started_at"),
                ended_at=d.get("ended_at"),
            )
            for d in debates_data["items"]
        ]
        
        return DebateListResponse(
            items=items,
            next_cursor=debates_data.get("next_cursor")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list debates: {str(e)}"
        )


@router.post("/debates/run", response_model=DebateRunResponse, status_code=status.HTTP_200_OK)
async def run_debate(request: DebateRunRequest):
    """
    Run a 5-turn debate with 3 agents
    
    M1 scope:
    - Accepts problem statement + 3 agent configs + OpenRouter key
    - Runs deterministic 5-turn round-robin
    - Persists debate + events to database
    - Returns summary + minutes + action items + event history
    
    Raises:
        400: Invalid request (wrong number of agents, missing fields)
        401: Invalid OpenRouter API key
        500: Internal server error
    """
    # Validate agent count
    if len(request.agents) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly 3 agents required for M1"
        )
    
    try:
        # Initialize engine with BYOK
        engine = DebateEngine(openrouter_api_key=request.openrouter_api_key)
        
        # Convert agents to dict format
        agents_list = [
            {
                'name': agent.name,
                'role': agent.role,
                'model_id': agent.model_id
            }
            for agent in request.agents
        ]
        
        # Run debate
        result = engine.run_debate(
            problem_statement=request.problem_statement,
            agents=agents_list,
            debate_title=request.debate_title
        )
        
        return result
    
    except OpenRouterAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OpenRouter authentication failed: {str(e)}"
        )
    except OpenRouterError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenRouter API error: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/debates/{debate_id}", response_model=DebateResponse)
async def get_debate(
    debate_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get debate by ID
    
    Protected: Requires valid JWT and workspace access
    
    Raises:
        401: Unauthorized
        403: Forbidden (workspace access denied)
        404: Debate not found
    """
    service = DebateService()
    debate = service.get_debate(debate_id)
    
    if not debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debate {debate_id} not found"
        )
    
    # Check workspace access (raises HTTPException if denied)
    check_workspace_access(current_user, debate['workspace_id'])
    
    # Fetch participants
    participants = service.get_participants(debate_id)
    participant_list = [
        {
            "participant_id": p['participant_id'],
            "participant_type": p.get('participant_type', 'agent'),
            "role_name": p.get('role_name', 'Unknown'),
            "agent_config": p.get('agent_config'),
            "created_at": p['created_at'].isoformat() if p.get('created_at') else None
        }
        for p in participants
    ]
    
    return DebateResponse(
        debate_id=debate['debate_id'],
        workspace_id=debate['workspace_id'],
        title=debate['title'],
        state=debate['state'],
        created_at=debate['created_at'].isoformat(),
        participants=participant_list
    )


@router.post("/debates", response_model=DebateResponse, status_code=status.HTTP_201_CREATED)
async def create_debate(
    request: CreateDebateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create new debate in pending state (M2)
    
    Protected: Requires valid JWT
    
    Raises:
        401: Unauthorized (missing/invalid token)
        403: Forbidden (workspace access denied)
        400: Invalid request
        500: Internal server error
    """
    # Verify user has access to requested workspace
    check_workspace_access(current_user, request.workspace_id)
    
    try:
        service = DebateService()
        debate = service.create_debate(
            workspace_id=request.workspace_id,
            title=request.title,
            policy_config=request.policy_config
        )
        
        return DebateResponse(
            debate_id=debate['debate_id'],
            workspace_id=debate['workspace_id'],
            title=debate['title'],
            state=debate['state'],
            created_at=debate['created_at'].isoformat()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/debates/{debate_id}/start", response_model=DebateResponse)
async def start_debate(
    debate_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Start debate (pending -> running)
    
    Protected: Requires valid JWT and workspace access
    
    Raises:
        401: Unauthorized
        403: Forbidden (workspace access denied)
        400: Invalid state transition
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
    
    # Check workspace access (raises HTTPException if denied)
    check_workspace_access(current_user, debate['workspace_id'])
    
    try:
        debate = service.start_debate(debate_id)
        
        return DebateResponse(
            debate_id=debate['debate_id'],
            workspace_id=debate['workspace_id'],
            title=debate['title'],
            state=debate['state'],
            created_at=debate['created_at'].isoformat()
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/debates/{debate_id}/pause", response_model=DebateResponse)
async def pause_debate(
    debate_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Pause debate (running -> paused)
    
    Protected: Requires valid JWT and workspace access
    
    Raises:
        401: Unauthorized
        403: Forbidden
        400: Invalid state transition
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
        debate = service.pause_debate(debate_id)
        
        return DebateResponse(
            debate_id=debate['debate_id'],
            workspace_id=debate['workspace_id'],
            title=debate['title'],
            state=debate['state'],
            created_at=debate['created_at'].isoformat()
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/debates/{debate_id}/resume", response_model=DebateResponse)
async def resume_debate(
    debate_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Resume debate (paused -> running)
    
    Protected: Requires valid JWT and workspace access
    
    Raises:
        401: Unauthorized
        403: Forbidden
        400: Invalid state transition
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
        debate = service.resume_debate(debate_id)
        
        return DebateResponse(
            debate_id=debate['debate_id'],
            workspace_id=debate['workspace_id'],
            title=debate['title'],
            state=debate['state'],
            created_at=debate['created_at'].isoformat()
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/debates/{debate_id}/intervene", response_model=InterventionResponse)
async def intervene_debate(
    debate_id: str,
    request: InterveneRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add intervention to debate
    
    Protected: Requires valid JWT and workspace access
    
    Raises:
        401: Unauthorized
        403: Forbidden
        400: Invalid state for intervention
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
        result = service.intervene(
            debate_id=debate_id,
            message=request.message,
            tagged_agents=request.tagged_agents
        )
        
        return InterventionResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/debates/{debate_id}/end", response_model=DebateResponse)
async def end_debate(
    debate_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    End debate (running/paused -> ended)
    
    Protected: Requires valid JWT and workspace access
    
    Raises:
        401: Unauthorized
        403: Forbidden
        400: Invalid state transition
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
        debate = service.end_debate(debate_id)
        
        return DebateResponse(
            debate_id=debate['debate_id'],
            workspace_id=debate['workspace_id'],
            title=debate['title'],
            state=debate['state'],
            created_at=debate['created_at'].isoformat()
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute turn: {str(e)}"
        )


@router.post("/debates/setup", response_model=DebateSetupResponse, status_code=status.HTTP_201_CREATED)
async def setup_debate(
    request: DebateSetupRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a debate with participants + materials in one call (M4 setup primitives).

    Protected: Requires valid JWT and workspace access.
    """
    check_workspace_access(current_user, request.workspace_id)

    svc = MeetingSetupService()
    try:
        debate_id, participant_ids, material_ids = svc.create_setup(
            workspace_id=request.workspace_id,
            title=request.title,
            problem_statement=request.problem_statement,
            timebox_minutes=request.timebox_minutes,
            participants=[
                p.model_dump(exclude_none=True, by_alias=True) for p in request.participants
            ],
            materials=[m.model_dump(exclude_none=True) for m in (request.materials or [])],
        )
    except MeetingSetupError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return DebateSetupResponse(
        debate_id=debate_id,
        participant_ids=participant_ids,
        material_ids=material_ids,
    )


@router.post("/debates/{debate_id}/summarize", response_model=SummaryResponse, status_code=status.HTTP_200_OK)
async def generate_summary(
    debate_id: str,
    request: SummarizeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate end-of-meeting summary, minutes, and action items (M3)
    
    Requires debate to be in 'ended' state.
    Uses OpenRouter BYOK - key is never stored.
    
    Protected: Requires valid JWT and workspace access
    
    Raises:
        401: Unauthorized
        403: Forbidden (workspace access denied)
        404: Debate not found
        400: Debate not ended or generation failed
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
        summary_service = SummaryService()
        outputs = summary_service.generate_summary(
            debate_id=debate_id,
            openrouter_api_key=request.openrouter_api_key,
            model_id=request.model_id
        )
        
        # Fetch saved record to get IDs
        saved = summary_service.get_summary(debate_id)
        
        return SummaryResponse(
            output_id=saved['output_id'],
            debate_id=saved['debate_id'],
            summary=saved['summary'],
            minutes=saved['minutes'],
            action_items=[ActionItem(**item) for item in saved['action_items']],
            generated_at=saved['generated_at'].isoformat(),
            model_used=saved['model_used']
        )
    
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
    except OpenRouterError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenRouter error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/debates/{debate_id}/summary", response_model=SummaryResponse)
async def get_summary(
    debate_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get existing debate summary/minutes/action items (M3)
    
    Protected: Requires valid JWT and workspace access
    
    Raises:
        401: Unauthorized
        403: Forbidden (workspace access denied)
        404: Debate not found or summary not generated
    """
    service = DebateService()
    debate = service.get_debate(debate_id)
    
    if not debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debate {debate_id} not found"
        )
    
    check_workspace_access(current_user, debate['workspace_id'])
    
    summary_service = SummaryService()
    outputs = summary_service.get_summary(debate_id)
    
    if not outputs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary not generated for debate {debate_id}"
        )
    
    return SummaryResponse(
        output_id=outputs['output_id'],
        debate_id=outputs['debate_id'],
        summary=outputs['summary'],
        minutes=outputs['minutes'],
        action_items=[ActionItem(**item) for item in outputs['action_items']],
        generated_at=outputs['generated_at'].isoformat(),
        model_used=outputs['model_used']
    )
