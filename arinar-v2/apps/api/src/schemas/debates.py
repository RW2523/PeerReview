"""Pydantic models for debate-related endpoints"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from .agents import AgentInput


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


class ParticipantInfo(BaseModel):
    """Participant information"""
    participant_id: str
    participant_type: str
    role_name: str
    agent_config: Optional[Dict[str, Any]] = None
    created_at: str


class DebateResponse(BaseModel):
    """Debate response"""
    debate_id: str
    workspace_id: str
    title: str
    state: str
    created_at: str
    participants: List[ParticipantInfo] = Field(default_factory=list, description="Debate participants")


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


class DebateListItem(BaseModel):
    """Single debate item in list"""
    debate_id: str
    workspace_id: str
    title: str
    state: str
    created_at: str
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None


class DebateListResponse(BaseModel):
    """Response for listing debates"""
    items: List[DebateListItem]
    next_cursor: Optional[str] = None
