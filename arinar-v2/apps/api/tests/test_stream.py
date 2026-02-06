"""Tests for SSE event streaming"""
import pytest
import os
import sys
import jwt
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from src.main import app
from src.config import settings


client = TestClient(app)


def generate_test_jwt(
    user_id: str = "user-123",
    workspace_id: str = "00000000-0000-0000-0000-000000000101",
    tenant_id: str = "tenant-789"
) -> str:
    """Generate test JWT token"""
    payload = {
        'sub': user_id,
        'workspace_id': workspace_id,
        'tenant_id': tenant_id,
        'email': 'test@example.com',
        'role': 'user',
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm='HS256')


@pytest.fixture
def enable_auth():
    """Enable auth for testing"""
    original = settings.require_auth
    settings.require_auth = True
    yield
    settings.require_auth = original


@pytest.fixture
def mock_debate_running():
    """Mock running debate"""
    return {
        'debate_id': 'debate-123',
        'workspace_id': '00000000-0000-0000-0000-000000000101',
        'title': 'Test Debate',
        'state': 'running',
        'policy_config': {},
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }


@pytest.fixture
def mock_debate_ended():
    """Mock ended debate"""
    return {
        'debate_id': 'debate-123',
        'workspace_id': '00000000-0000-0000-0000-000000000101',
        'title': 'Test Debate',
        'state': 'ended',
        'policy_config': {},
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }


@pytest.fixture
def mock_events():
    """Mock debate events"""
    return [
        {
            'event_id': 'event-1',
            'debate_id': 'debate-123',
            'event_type': 'system_start',
            'sequence_number': 1,
            'occurred_at': datetime.now(timezone.utc),
            'payload': {'action': 'started'},
            'agent_id': None,
            'participant_id': None
        },
        {
            'event_id': 'event-2',
            'debate_id': 'debate-123',
            'event_type': 'agent_message',
            'sequence_number': 2,
            'occurred_at': datetime.now(timezone.utc),
            'payload': {'content': 'Test message'},
            'agent_id': 'agent-1',
            'participant_id': 'participant-1'
        }
    ]


@patch('src.main.DebateService')
@patch('src.main.StreamService')
def test_stream_unauthorized(mock_stream_class, mock_service_class, enable_auth):
    """Test stream endpoint without authorization"""
    response = client.get("/debates/debate-123/events/stream")
    
    assert response.status_code == 401
    assert "Missing authorization token" in response.json()['detail']


@patch('src.main.DebateService')
@patch('src.main.StreamService')
def test_stream_cross_workspace_access(
    mock_stream_class,
    mock_service_class,
    enable_auth,
    mock_debate_running
):
    """Test stream endpoint with cross-workspace token"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.get_debate.return_value = mock_debate_running
    
    # User in different workspace
    token = generate_test_jwt(workspace_id='workspace-different')
    
    response = client.get(
        "/debates/debate-123/events/stream",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 403
    assert "different workspace" in response.json()['detail']


@patch('src.main.DebateService')
@patch('src.main.StreamService')
def test_stream_debate_not_found(
    mock_stream_class,
    mock_service_class,
    enable_auth
):
    """Test stream endpoint for non-existent debate"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.get_debate.return_value = None
    
    token = generate_test_jwt()
    
    response = client.get(
        "/debates/debate-999/events/stream",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()['detail'].lower()


@patch('src.main.DebateService')
@patch('src.main.StreamService')
def test_stream_authorized_success(
    mock_stream_class,
    mock_service_class,
    enable_auth,
    mock_debate_running
):
    """Test stream endpoint with valid authorization"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.get_debate.return_value = mock_debate_running
    
    # Mock stream service
    async def mock_stream_generator(debate_id, since_sequence=None):
        yield "event: debate_event\ndata: {}\n\n"
        yield "event: state_update\ndata: {}\n\n"
    
    mock_stream = MagicMock()
    mock_stream_class.return_value = mock_stream
    mock_stream.stream_debate_events.return_value = mock_stream_generator('debate-123')
    
    token = generate_test_jwt()
    
    response = client.get(
        "/debates/debate-123/events/stream",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.headers['content-type'] == 'text/event-stream; charset=utf-8'
    assert response.headers['cache-control'] == 'no-cache'


def test_stream_service_ended_debate(mock_debate_ended, mock_events):
    """Test stream service terminates for ended debate"""
    from src.stream_service import StreamService
    
    service = StreamService()
    
    # Mock internal methods
    service._get_debate = MagicMock(return_value=mock_debate_ended)
    service._get_events = MagicMock(return_value=mock_events)
    
    # Collect stream events
    import asyncio
    
    async def collect_events():
        events = []
        async for event in service.stream_debate_events('debate-123'):
            events.append(event)
        return events
    
    events = asyncio.run(collect_events())
    
    # Should have events + state_update + stream_end
    assert len(events) >= 3
    
    # Last event should be stream_end
    last_event = events[-1]
    assert 'stream_end' in last_event
    assert 'debate_ended' in last_event


def test_stream_service_running_debate(mock_debate_running, mock_events):
    """Test stream service continues for running debate"""
    from src.stream_service import StreamService
    
    service = StreamService()
    
    # Mock internal methods
    service._get_debate = MagicMock(return_value=mock_debate_running)
    service._get_events = MagicMock(return_value=mock_events)
    
    # Collect stream events
    import asyncio
    
    async def collect_events():
        events = []
        async for event in service.stream_debate_events('debate-123'):
            events.append(event)
            # Stop after a few events (would continue indefinitely in real scenario)
            if len(events) >= 5:
                break
        return events
    
    events = asyncio.run(collect_events())
    
    # Should have events + state_update + keepalive
    assert len(events) >= 3
    
    # Should NOT have stream_end for running debate
    all_events_text = ''.join(events)
    assert 'stream_end' not in all_events_text
    assert 'keepalive' in all_events_text


def test_stream_service_since_parameter(mock_debate_running):
    """Test stream service respects since parameter"""
    from src.stream_service import StreamService
    
    service = StreamService()
    
    # Mock internal methods
    service._get_debate = MagicMock(return_value=mock_debate_running)
    
    # Mock events with different sequence numbers
    all_events = [
        {'event_id': 'e1', 'debate_id': 'd1', 'event_type': 'start',
         'sequence_number': 1, 'occurred_at': datetime.now(timezone.utc),
         'payload': {}, 'agent_id': None, 'participant_id': None},
        {'event_id': 'e2', 'debate_id': 'd1', 'event_type': 'msg',
         'sequence_number': 2, 'occurred_at': datetime.now(timezone.utc),
         'payload': {}, 'agent_id': None, 'participant_id': None},
        {'event_id': 'e3', 'debate_id': 'd1', 'event_type': 'msg',
         'sequence_number': 3, 'occurred_at': datetime.now(timezone.utc),
         'payload': {}, 'agent_id': None, 'participant_id': None}
    ]
    
    # When since=1, should only get events with sequence > 1
    service._get_events = MagicMock(return_value=[e for e in all_events if e['sequence_number'] > 1])
    
    import asyncio
    
    async def collect_events():
        events = []
        async for event in service.stream_debate_events('debate-123', since_sequence=1):
            if 'debate_event' in event:
                events.append(event)
            if len(events) >= 2:
                break
        return events
    
    events = asyncio.run(collect_events())
    
    # Should have called _get_events with since_sequence=1
    service._get_events.assert_called_once_with('debate-123', 1)
    
    # Should have 2 events (sequence 2 and 3)
    assert len(events) == 2
