"""
Preflight API Routes
Endpoints for agent preparation orchestration
"""

import psycopg2
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.config import settings
from src.auth import require_auth
from src.tasks.preflight import orchestrate_preflight

router = APIRouter()


# Request/Response Models

class PreflightStartResponse(BaseModel):
    run_id: str
    debate_id: str
    status: str
    participant_count: int
    participant_runs: List[Dict[str, Any]]


class ParticipantRunStatus(BaseModel):
    participant_run_id: str
    participant_id: str
    agent_id: Optional[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
    skip_reason: Optional[str]
    prep_pack_knowledge_id: Optional[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PreflightStatusResponse(BaseModel):
    run_id: str
    debate_id: str
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
    participant_runs: List[ParticipantRunStatus]


class PreflightRetryRequest(BaseModel):
    participant_id: str


class PreflightSkipRequest(BaseModel):
    participant_id: str
    reason: str


class PreflightActionResponse(BaseModel):
    participant_run_id: str
    participant_id: str
    status: str
    message: str


# Helper functions

def check_workspace_access(workspace_id: str, auth_workspace_id: str):
    """Check if user has access to workspace"""
    if workspace_id != auth_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )


def get_debate_workspace(debate_id: str) -> str:
    """Get workspace_id for a debate"""
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT workspace_id FROM debates WHERE debate_id = %s", (debate_id,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Debate {debate_id} not found"
            )
        return result[0]
    finally:
        cursor.close()
        conn.close()


# Endpoints

@router.post("/debates/{debate_id}/preflight/start", response_model=PreflightStartResponse)
def start_preflight(
    debate_id: str,
    workspace_id: str = Depends(require_auth)
):
    """
    Start preflight preparation for all participants in a debate
    
    Creates a preflight run and enqueues tasks to generate prep packs for each participant.
    
    Protected: Requires valid JWT and workspace access
    """
    # Check workspace access
    debate_workspace = get_debate_workspace(debate_id)
    check_workspace_access(debate_workspace, workspace_id)
    
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        # Check if a preflight run already exists for this debate
        cursor.execute("""
            SELECT run_id, status FROM preflight_runs WHERE debate_id = %s
        """, (debate_id,))
        
        existing_run = cursor.fetchone()
        if existing_run:
            run_id, existing_status = existing_run
            if existing_status in ('queued', 'running'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Preflight already {existing_status} for this debate"
                )
            
            # Delete old run to start fresh
            cursor.execute("DELETE FROM preflight_runs WHERE run_id = %s", (run_id,))
            conn.commit()
        
        # Create new preflight run
        cursor.execute("""
            INSERT INTO preflight_runs (run_id, debate_id, status, created_at)
            VALUES (gen_random_uuid(), %s, 'queued', NOW())
            RETURNING run_id
        """, (debate_id,))
        
        run_id = cursor.fetchone()[0]
        
        # Get all participants for this debate
        cursor.execute("""
            SELECT participant_id, agent_config
            FROM participants
            WHERE debate_id = %s
        """, (debate_id,))
        
        participants = cursor.fetchall()
        
        if not participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No participants found for this debate"
            )
        
        # Create participant run entries
        participant_runs = []
        for participant_id, agent_config in participants:
            agent_id = agent_config.get('agent_id') if agent_config else None
            
            cursor.execute("""
                INSERT INTO preflight_participant_runs (
                    participant_run_id, run_id, participant_id, agent_id, status, metadata
                ) VALUES (
                    gen_random_uuid(), %s, %s, %s, 'queued', '{}'::jsonb
                )
                RETURNING participant_run_id, participant_id, agent_id, status
            """, (run_id, participant_id, agent_id))
            
            participant_run = cursor.fetchone()
            participant_runs.append({
                'participant_run_id': participant_run[0],
                'participant_id': participant_run[1],
                'agent_id': participant_run[2],
                'status': participant_run[3]
            })
        
        conn.commit()
        
        # Enqueue Celery task
        orchestrate_preflight.delay(run_id, debate_id)
        
        return PreflightStartResponse(
            run_id=run_id,
            debate_id=debate_id,
            status='queued',
            participant_count=len(participant_runs),
            participant_runs=participant_runs
        )
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start preflight: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@router.get("/debates/{debate_id}/preflight/status", response_model=PreflightStatusResponse)
def get_preflight_status(
    debate_id: str,
    workspace_id: str = Depends(require_auth)
):
    """
    Get preflight preparation status for a debate
    
    Returns overall run status and per-participant progress.
    
    Protected: Requires valid JWT and workspace access
    """
    # Check workspace access
    debate_workspace = get_debate_workspace(debate_id)
    check_workspace_access(debate_workspace, workspace_id)
    
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        # Get preflight run
        cursor.execute("""
            SELECT run_id, debate_id, status, created_at, started_at, completed_at, error
            FROM preflight_runs
            WHERE debate_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (debate_id,))
        
        run = cursor.fetchone()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No preflight run found for this debate"
            )
        
        run_id, debate_id, run_status, created_at, started_at, completed_at, error = run
        
        # Get participant runs
        cursor.execute("""
            SELECT 
                participant_run_id, participant_id, agent_id, status,
                started_at, completed_at, error, skip_reason,
                prep_pack_knowledge_id, metadata
            FROM preflight_participant_runs
            WHERE run_id = %s
            ORDER BY started_at ASC NULLS LAST
        """, (run_id,))
        
        participant_runs = []
        for row in cursor.fetchall():
            participant_runs.append(ParticipantRunStatus(
                participant_run_id=row[0],
                participant_id=row[1],
                agent_id=row[2],
                status=row[3],
                started_at=row[4],
                completed_at=row[5],
                error=row[6],
                skip_reason=row[7],
                prep_pack_knowledge_id=row[8],
                metadata=row[9] or {}
            ))
        
        return PreflightStatusResponse(
            run_id=run_id,
            debate_id=debate_id,
            status=run_status,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            error=error,
            participant_runs=participant_runs
        )
    
    finally:
        cursor.close()
        conn.close()


@router.post("/debates/{debate_id}/preflight/retry", response_model=PreflightActionResponse)
def retry_participant_preflight(
    debate_id: str,
    request: PreflightRetryRequest,
    workspace_id: str = Depends(require_auth)
):
    """
    Retry preflight preparation for a specific participant
    
    Only allowed if participant status is 'failed'.
    
    Protected: Requires valid JWT and workspace access
    """
    # Check workspace access
    debate_workspace = get_debate_workspace(debate_id)
    check_workspace_access(debate_workspace, workspace_id)
    
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        # Get current run and participant run
        cursor.execute("""
            SELECT pr.run_id, pr.participant_run_id, pr.status
            FROM preflight_runs r
            JOIN preflight_participant_runs pr ON r.run_id = pr.run_id
            WHERE r.debate_id = %s AND pr.participant_id = %s
            ORDER BY r.created_at DESC
            LIMIT 1
        """, (debate_id, request.participant_id))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participant preflight run not found"
            )
        
        run_id, participant_run_id, current_status = result
        
        if current_status != 'failed':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Can only retry failed runs. Current status: {current_status}"
            )
        
        # Reset participant run to queued
        cursor.execute("""
            UPDATE preflight_participant_runs
            SET status = 'queued', error = NULL, started_at = NULL, completed_at = NULL
            WHERE participant_run_id = %s
        """, (participant_run_id,))
        conn.commit()
        
        # Re-enqueue the task
        from src.tasks.preflight import prepare_participant_preflight
        prepare_participant_preflight(participant_run_id, request.participant_id, debate_id)
        
        return PreflightActionResponse(
            participant_run_id=participant_run_id,
            participant_id=request.participant_id,
            status='queued',
            message='Retry queued successfully'
        )
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@router.post("/debates/{debate_id}/preflight/skip", response_model=PreflightActionResponse)
def skip_participant_preflight(
    debate_id: str,
    request: PreflightSkipRequest,
    workspace_id: str = Depends(require_auth)
):
    """
    Skip preflight preparation for a specific participant
    
    Allowed if participant status is queued, running, or failed.
    Records skip reason for audit trail.
    
    Protected: Requires valid JWT and workspace access
    """
    # Check workspace access
    debate_workspace = get_debate_workspace(debate_id)
    check_workspace_access(debate_workspace, workspace_id)
    
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        # Get current run and participant run
        cursor.execute("""
            SELECT pr.run_id, pr.participant_run_id, pr.status
            FROM preflight_runs r
            JOIN preflight_participant_runs pr ON r.run_id = pr.run_id
            WHERE r.debate_id = %s AND pr.participant_id = %s
            ORDER BY r.created_at DESC
            LIMIT 1
        """, (debate_id, request.participant_id))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participant preflight run not found"
            )
        
        run_id, participant_run_id, current_status = result
        
        if current_status in ('success', 'skipped'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot skip completed runs. Current status: {current_status}"
            )
        
        # Update to skipped
        cursor.execute("""
            UPDATE preflight_participant_runs
            SET status = 'skipped', skip_reason = %s, completed_at = NOW()
            WHERE participant_run_id = %s
        """, (request.reason, participant_run_id))
        conn.commit()
        
        return PreflightActionResponse(
            participant_run_id=participant_run_id,
            participant_id=request.participant_id,
            status='skipped',
            message=f'Skipped: {request.reason}'
        )
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to skip: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()
