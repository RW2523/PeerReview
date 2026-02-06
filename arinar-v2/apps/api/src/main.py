"""FastAPI application entry point"""
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from .config import settings
from .debate_engine import DebateEngine
from .debate_service import DebateService
from .stream_service import StreamService
from .openrouter_client import OpenRouterAuthError, OpenRouterError
from .state_machine import StateTransitionError
from .auth import get_current_user, check_workspace_access


app = FastAPI(
    title="Arinar Debate API",
    description="M1/M2: Debate API with realtime controls",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class AgentInput(BaseModel):
    """Agent configuration for debate"""
    model_config = ConfigDict(protected_namespaces=())
    
    name: str = Field(..., description="Agent display name")
    role: str = Field(..., description="Agent role description")
    model_id: str = Field(..., description="OpenRouter model ID (e.g. anthropic/claude-3.5-sonnet)")


class DebateRunRequest(BaseModel):
    """Request to run a debate"""
    problem_statement: str = Field(..., description="Problem to discuss")
    agents: List[AgentInput] = Field(..., description="Exactly 3 agents for M1")
    openrouter_api_key: str = Field(..., description="OpenRouter API key (BYOK)")
    debate_title: str = Field(default="Untitled Debate", description="Optional debate title")


class DebateRunResponse(BaseModel):
    """Response from debate run"""
    debate_id: str
    status: str
    outputs: Dict[str, Any]
    event_history: List[Dict[str, Any]]


class CreateDebateRequest(BaseModel):
    """Request to create a debate"""
    workspace_id: str = Field(..., description="Workspace ID")
    title: str = Field(..., description="Debate title")
    policy_config: Optional[Dict[str, Any]] = Field(default=None, description="Policy configuration")


class DebateResponse(BaseModel):
    """Debate response"""
    debate_id: str
    workspace_id: str
    title: str
    state: str
    created_at: str


class InterveneRequest(BaseModel):
    """Request to intervene in debate"""
    message: str = Field(..., description="Intervention message", min_length=1)
    tagged_agents: Optional[List[str]] = Field(default=None, description="Agent names to tag")


class InterventionResponse(BaseModel):
    """Response from intervention"""
    event_id: str
    debate_id: str
    message: str
    tagged_agents: List[str]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "arinar-api",
        "version": "1.0.0"
    }


@app.post("/debates/run", response_model=DebateRunResponse, status_code=status.HTTP_200_OK)
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


@app.post("/debates", response_model=DebateResponse, status_code=status.HTTP_201_CREATED)
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


@app.post("/debates/{debate_id}/start", response_model=DebateResponse)
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


@app.post("/debates/{debate_id}/pause", response_model=DebateResponse)
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


@app.post("/debates/{debate_id}/resume", response_model=DebateResponse)
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


@app.post("/debates/{debate_id}/intervene", response_model=InterventionResponse)
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


@app.post("/debates/{debate_id}/end", response_model=DebateResponse)
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


@app.get("/debates/{debate_id}/events/stream")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug
    )
