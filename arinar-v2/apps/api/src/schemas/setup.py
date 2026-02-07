"""Pydantic models for meeting setup endpoints"""
from pydantic import BaseModel, Field
from typing import List, Optional
from .agents import SetupParticipant


class SetupMaterial(BaseModel):
    """Material metadata for setup"""
    kind: str = Field(..., pattern="^(text|link|file_placeholder)$")
    title: Optional[str] = None
    body_text: Optional[str] = None
    url: Optional[str] = None


class DebateSetupRequest(BaseModel):
    """Request to create debate with full setup"""
    workspace_id: str
    title: str
    problem_statement: str
    timebox_minutes: Optional[int] = None
    participants: List[SetupParticipant]
    materials: Optional[List[SetupMaterial]] = Field(default_factory=list)


class DebateSetupResponse(BaseModel):
    """Response from debate setup"""
    debate_id: str
    participant_ids: List[str]
    material_ids: List[str]
