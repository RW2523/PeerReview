"""Tests for M2 debate control endpoints"""
import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from src.main import app
from src.state_machine import DebateState, StateTransitionError
from src.config import settings


client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_auth_for_control_tests():
    """Disable auth requirement for control logic tests"""
    original = settings.require_auth
    settings.require_auth = False
    yield
    settings.require_auth = original


@pytest.fixture
def mock_debate_pending():
    """Mock debate in pending state"""
    return {
        'debate_id': 'debate-123',
        'workspace_id': '00000000-0000-0000-0000-000000000101',  # Match test user workspace
        'title': 'Test Debate',
        'state': 'pending',
        'policy_config': {},
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }


@pytest.fixture
def mock_debate_running():
    """Mock debate in running state"""
    return {
        'debate_id': 'debate-123',
        'workspace_id': '00000000-0000-0000-0000-000000000101',  # Match test user workspace
        'title': 'Test Debate',
        'state': 'running',
        'policy_config': {},
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }


@pytest.fixture
def mock_debate_paused():
    """Mock debate in paused state"""
    return {
        'debate_id': 'debate-123',
        'workspace_id': '00000000-0000-0000-0000-000000000101',  # Match test user workspace
        'title': 'Test Debate',
        'state': 'paused',
        'policy_config': {},
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }


@pytest.fixture
def mock_debate_ended():
    """Mock debate in ended state"""
    return {
        'debate_id': 'debate-123',
        'workspace_id': '00000000-0000-0000-0000-000000000101',  # Match test user workspace
        'title': 'Test Debate',
        'state': 'ended',
        'policy_config': {},
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }


@patch('src.main.DebateService')
def test_create_debate(mock_service_class):
    """Test creating a new debate"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.create_debate.return_value = {
        'debate_id': 'debate-new',
        'workspace_id': '00000000-0000-0000-0000-000000000101',
        'title': 'New Debate',
        'state': 'pending',
        'created_at': datetime.now(timezone.utc)
    }
    
    response = client.post("/debates", json={
        "workspace_id": "00000000-0000-0000-0000-000000000101",
        "title": "New Debate"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data['debate_id'] == 'debate-new'
    assert data['state'] == 'pending'


@patch('src.main.DebateService')
def test_start_debate_from_pending(mock_service_class, mock_debate_pending, mock_debate_running):
    """Test starting a debate from pending state"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_pending
    mock_service.start_debate.return_value = mock_debate_running
    
    response = client.post("/debates/debate-123/start")
    
    assert response.status_code == 200
    data = response.json()
    assert data['state'] == 'running'


@patch('src.main.DebateService')
def test_start_debate_invalid_state(mock_service_class, mock_debate_running):
    """Test starting debate from invalid state"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_running
    mock_service.start_debate.side_effect = StateTransitionError(
        "Cannot start debate in running state"
    )
    
    response = client.post("/debates/debate-123/start")
    
    assert response.status_code == 400
    assert "Cannot start debate" in response.json()['detail']


@patch('src.main.DebateService')
def test_pause_debate_from_running(mock_service_class, mock_debate_running, mock_debate_paused):
    """Test pausing a running debate"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_running
    mock_service.pause_debate.return_value = mock_debate_paused
    
    response = client.post("/debates/debate-123/pause")
    
    assert response.status_code == 200
    data = response.json()
    assert data['state'] == 'paused'


@patch('src.main.DebateService')
def test_pause_debate_invalid_state(mock_service_class, mock_debate_pending):
    """Test pausing debate from invalid state"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_pending
    mock_service.pause_debate.side_effect = StateTransitionError(
        "Cannot pause debate in pending state"
    )
    
    response = client.post("/debates/debate-123/pause")
    
    assert response.status_code == 400
    assert "Cannot pause debate" in response.json()['detail']


@patch('src.main.DebateService')
def test_resume_debate_from_paused(mock_service_class, mock_debate_paused, mock_debate_running):
    """Test resuming a paused debate"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_paused
    mock_service.resume_debate.return_value = mock_debate_running
    
    response = client.post("/debates/debate-123/resume")
    
    assert response.status_code == 200
    data = response.json()
    assert data['state'] == 'running'


@patch('src.main.DebateService')
def test_resume_debate_invalid_state(mock_service_class, mock_debate_running):
    """Test resuming debate from invalid state"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_running
    mock_service.resume_debate.side_effect = StateTransitionError(
        "Cannot resume debate in running state"
    )
    
    response = client.post("/debates/debate-123/resume")
    
    assert response.status_code == 400
    assert "Cannot resume debate" in response.json()['detail']


@patch('src.main.DebateService')
def test_intervene_in_running_debate(mock_service_class, mock_debate_running):
    """Test intervention in running debate"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_running
    mock_service.intervene.return_value = {
        'event_id': 'event-789',
        'debate_id': 'debate-123',
        'message': 'Please focus on cost analysis',
        'tagged_agents': ['Product Manager']
    }
    
    response = client.post("/debates/debate-123/intervene", json={
        "message": "Please focus on cost analysis",
        "tagged_agents": ["Product Manager"]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data['message'] == 'Please focus on cost analysis'
    assert 'Product Manager' in data['tagged_agents']


@patch('src.main.DebateService')
def test_intervene_in_invalid_state(mock_service_class, mock_debate_ended):
    """Test intervention in ended debate (should fail)"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_ended
    mock_service.intervene.side_effect = StateTransitionError(
        "Cannot intervene in debate in ended state"
    )
    
    response = client.post("/debates/debate-123/intervene", json={
        "message": "Too late!"
    })
    
    assert response.status_code == 400
    assert "Cannot intervene" in response.json()['detail']


@patch('src.main.DebateService')
def test_end_debate_from_running(mock_service_class, mock_debate_running, mock_debate_ended):
    """Test ending a running debate"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_running
    mock_service.end_debate.return_value = mock_debate_ended
    
    response = client.post("/debates/debate-123/end")
    
    assert response.status_code == 200
    data = response.json()
    assert data['state'] == 'ended'


@patch('src.main.DebateService')
def test_end_debate_from_paused(mock_service_class, mock_debate_paused, mock_debate_ended):
    """Test ending a paused debate"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_paused
    mock_service.end_debate.return_value = mock_debate_ended
    
    response = client.post("/debates/debate-123/end")
    
    assert response.status_code == 200
    data = response.json()
    assert data['state'] == 'ended'


@patch('src.main.DebateService')
def test_end_debate_invalid_state(mock_service_class, mock_debate_ended):
    """Test ending debate from invalid state"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.get_debate.return_value = mock_debate_ended
    mock_service.end_debate.side_effect = StateTransitionError(
        "Cannot end debate in ended state"
    )
    
    response = client.post("/debates/debate-123/end")
    
    assert response.status_code == 400
    assert "Cannot end debate" in response.json()['detail']


@patch('src.main.DebateService')
def test_debate_not_found(mock_service_class):
    """Test operations on non-existent debate"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    # Mock get_debate returning None (debate not found)
    mock_service.get_debate.return_value = None
    
    response = client.post("/debates/debate-999/start")
    
    assert response.status_code == 404
    assert "not found" in response.json()['detail'].lower()


def test_state_transition_validation():
    """Test state machine transition validation logic"""
    from src.state_machine import DebateStateMachine
    
    # Valid transitions
    assert DebateStateMachine.can_transition(DebateState.PENDING, DebateState.RUNNING)
    assert DebateStateMachine.can_transition(DebateState.RUNNING, DebateState.PAUSED)
    assert DebateStateMachine.can_transition(DebateState.RUNNING, DebateState.ENDED)
    assert DebateStateMachine.can_transition(DebateState.PAUSED, DebateState.RUNNING)
    assert DebateStateMachine.can_transition(DebateState.PAUSED, DebateState.ENDED)
    
    # Invalid transitions
    assert not DebateStateMachine.can_transition(DebateState.PENDING, DebateState.PAUSED)
    assert not DebateStateMachine.can_transition(DebateState.PENDING, DebateState.ENDED)
    assert not DebateStateMachine.can_transition(DebateState.ENDED, DebateState.RUNNING)
    assert not DebateStateMachine.can_transition(DebateState.ENDED, DebateState.PAUSED)
    
    # Action permissions
    assert DebateStateMachine.can_start(DebateState.PENDING)
    assert not DebateStateMachine.can_start(DebateState.RUNNING)
    
    assert DebateStateMachine.can_pause(DebateState.RUNNING)
    assert not DebateStateMachine.can_pause(DebateState.PAUSED)
    
    assert DebateStateMachine.can_resume(DebateState.PAUSED)
    assert not DebateStateMachine.can_resume(DebateState.RUNNING)
    
    assert DebateStateMachine.can_intervene(DebateState.RUNNING)
    assert DebateStateMachine.can_intervene(DebateState.PAUSED)
    assert not DebateStateMachine.can_intervene(DebateState.ENDED)
    
    assert DebateStateMachine.can_end(DebateState.RUNNING)
    assert DebateStateMachine.can_end(DebateState.PAUSED)
    assert not DebateStateMachine.can_end(DebateState.ENDED)
