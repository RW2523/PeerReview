"""Tests for Supabase Auth JWT validation and authorization"""
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
    workspace_id: str = "workspace-456",
    tenant_id: str = "tenant-789",
    expired: bool = False,
    invalid_signature: bool = False
) -> str:
    """Generate test JWT token"""
    payload = {
        'sub': user_id,
        'workspace_id': workspace_id,
        'tenant_id': tenant_id,
        'email': 'test@example.com',
        'role': 'user',
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=-1 if expired else 1)
    }
    
    secret = "wrong-secret" if invalid_signature else settings.supabase_jwt_secret
    
    return jwt.encode(payload, secret, algorithm='HS256')


@pytest.fixture
def enable_auth():
    """Enable auth for testing"""
    original = settings.require_auth
    settings.require_auth = True
    yield
    settings.require_auth = original


@pytest.fixture
def mock_debate():
    """Mock debate for auth tests"""
    return {
        'debate_id': 'debate-123',
        'workspace_id': 'workspace-456',
        'title': 'Test Debate',
        'state': 'pending',
        'created_at': datetime.now(timezone.utc)
    }


@patch('src.main.DebateService')
def test_create_debate_missing_token(mock_service_class, enable_auth):
    """Test create debate without authorization token"""
    response = client.post("/debates", json={
        "workspace_id": "workspace-456",
        "title": "New Debate"
    })
    
    assert response.status_code == 401
    assert "Missing authorization token" in response.json()['detail']


@patch('src.main.DebateService')
def test_create_debate_invalid_token(mock_service_class, enable_auth):
    """Test create debate with invalid token signature"""
    invalid_token = generate_test_jwt(invalid_signature=True)
    
    response = client.post("/debates", json={
        "workspace_id": "workspace-456",
        "title": "New Debate"
    }, headers={"Authorization": f"Bearer {invalid_token}"})
    
    assert response.status_code == 401
    assert "Invalid token signature" in response.json()['detail']


@patch('src.main.DebateService')
def test_create_debate_expired_token(mock_service_class, enable_auth):
    """Test create debate with expired token"""
    expired_token = generate_test_jwt(expired=True)
    
    response = client.post("/debates", json={
        "workspace_id": "workspace-456",
        "title": "New Debate"
    }, headers={"Authorization": f"Bearer {expired_token}"})
    
    assert response.status_code == 401
    assert "Token expired" in response.json()['detail']


@patch('src.main.DebateService')
def test_create_debate_valid_token(mock_service_class, enable_auth):
    """Test create debate with valid token"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    mock_service.create_debate.return_value = {
        'debate_id': 'debate-new',
        'workspace_id': 'workspace-456',
        'title': 'New Debate',
        'state': 'pending',
        'created_at': datetime.now(timezone.utc)
    }
    
    valid_token = generate_test_jwt(workspace_id='workspace-456')
    
    response = client.post("/debates", json={
        "workspace_id": "workspace-456",
        "title": "New Debate"
    }, headers={"Authorization": f"Bearer {valid_token}"})
    
    assert response.status_code == 201
    data = response.json()
    assert data['state'] == 'pending'


@patch('src.main.DebateService')
def test_start_debate_cross_workspace_access(mock_service_class, enable_auth, mock_debate):
    """Test starting debate from different workspace (should fail)"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.get_debate.return_value = mock_debate
    
    # User in workspace-999, debate in workspace-456
    token = generate_test_jwt(workspace_id='workspace-999')
    
    response = client.post("/debates/debate-123/start",
                          headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 403
    assert "different workspace" in response.json()['detail']


@patch('src.main.DebateService')
def test_pause_debate_valid_auth(mock_service_class, enable_auth, mock_debate):
    """Test pause debate with valid authorization"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    
    paused_debate = mock_debate.copy()
    paused_debate['state'] = 'paused'
    
    mock_service.get_debate.return_value = mock_debate
    mock_service.pause_debate.return_value = paused_debate
    
    token = generate_test_jwt(workspace_id='workspace-456')
    
    response = client.post("/debates/debate-123/pause",
                          headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 200
    assert response.json()['state'] == 'paused'


@patch('src.main.DebateService')
def test_intervene_missing_workspace_claim(mock_service_class, enable_auth, mock_debate):
    """Test intervention with token missing workspace_id claim"""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.get_debate.return_value = mock_debate
    
    # Generate token without workspace_id
    payload = {
        'sub': 'user-123',
        'email': 'test@example.com',
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.supabase_jwt_secret, algorithm='HS256')
    
    response = client.post("/debates/debate-123/intervene",
                          json={"message": "Test intervention"},
                          headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 403
    assert "not associated with any workspace" in response.json()['detail']


@patch('src.main.DebateService')
def test_end_debate_unauthorized(mock_service_class, enable_auth):
    """Test ending debate without authorization"""
    response = client.post("/debates/debate-123/end")
    
    assert response.status_code == 401
    assert "Missing authorization token" in response.json()['detail']


def test_health_check_no_auth_required():
    """Test health endpoint does not require authentication"""
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'
