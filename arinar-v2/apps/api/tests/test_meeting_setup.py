"""Tests for M4 meeting setup endpoints (TICKET-08B.1)"""
import pytest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_auth_for_setup_tests():
    """Disable auth requirement for setup tests"""
    from src.config import settings
    original = settings.require_auth
    settings.require_auth = False
    yield
    settings.require_auth = original


def test_get_agent_templates():
    """Test GET /agent-templates returns expected structure"""
    response = client.get("/agent-templates")
    
    assert response.status_code == 200
    templates = response.json()
    
    assert isinstance(templates, list)
    assert len(templates) >= 6  # At least 6 templates (roles + personas)
    
    # Check first template structure
    template = templates[0]
    assert 'template_id' in template
    assert 'label' in template
    assert 'role_title' in template
    assert 'system_prompt' in template
    assert 'model_id' in template
    assert 'model_config' in template
    
    # Verify we have role templates
    role_ids = [t['template_id'] for t in templates]
    assert 'pm' in role_ids
    assert 'engineer' in role_ids
    assert 'designer' in role_ids
    
    # Verify we have persona templates
    persona_ids = [t['template_id'] for t in templates if t['template_id'].startswith('persona-')]
    assert len(persona_ids) >= 2


def test_create_and_list_agents():
    """Test POST /agents then GET /agents"""
    workspace_id = '00000000-0000-0000-0000-000000000101'
    
    # Create agent
    create_response = client.post("/agents", json={
        "workspace_id": workspace_id,
        "name": "Test PM Agent",
        "role_description": "Product Manager for testing",
        "system_prompt": "You are a test product manager.",
        "model_id": "anthropic/claude-3.5-sonnet",
        "agent_model_config": {"temperature": 0.7, "max_tokens": 2000}
    })
    
    assert create_response.status_code == 201
    agent = create_response.json()
    
    assert 'agent_id' in agent
    assert agent['workspace_id'] == workspace_id
    assert agent['name'] == "Test PM Agent"
    assert agent['system_prompt'] == "You are a test product manager."
    assert agent['model_id'] == "anthropic/claude-3.5-sonnet"
    assert agent['model_config']['temperature'] == 0.7
    
    # List agents
    list_response = client.get(f"/agents?workspace_id={workspace_id}")
    
    assert list_response.status_code == 200
    agents = list_response.json()
    
    assert isinstance(agents, list)
    assert len(agents) > 0
    
    # Find our created agent
    created_agent = next((a for a in agents if a['agent_id'] == agent['agent_id']), None)
    assert created_agent is not None
    assert created_agent['name'] == "Test PM Agent"


def test_debate_setup_with_inline_participants():
    """Test POST /debates/setup with inline participant configs"""
    workspace_id = '00000000-0000-0000-0000-000000000101'
    
    response = client.post("/debates/setup", json={
        "workspace_id": workspace_id,
        "title": "Q1 Feature Planning",
        "problem_statement": "What features should we prioritize in Q1?",
        "timebox_minutes": 30,
        "participants": [
            {
                "name": "Product Manager",
                "role_description": "PM",
                "system_prompt": "You are a product manager.",
                "model_id": "anthropic/claude-3.5-sonnet",
                "model_config": {"temperature": 0.7}
            },
            {
                "name": "Engineer",
                "system_prompt": "You are an engineer.",
                "model_id": "anthropic/claude-3.5-sonnet",
                "model_config": {"temperature": 0.6}
            }
        ],
        "materials": [
            {
                "kind": "text",
                "title": "Context",
                "body_text": "Our users want better collaboration features."
            },
            {
                "kind": "link",
                "title": "User Research",
                "url": "https://example.com/research"
            }
        ]
    })
    
    assert response.status_code == 201
    data = response.json()
    
    assert 'debate_id' in data
    assert 'participant_ids' in data
    assert 'material_ids' in data
    
    assert len(data['participant_ids']) == 2
    assert len(data['material_ids']) == 2
    
    # Verify debate was created
    debate_id = data['debate_id']
    from src.debate_service import DebateService
    service = DebateService()
    debate = service.get_debate(debate_id)
    
    assert debate is not None
    assert debate['title'] == "Q1 Feature Planning"
    assert debate['state'] == 'pending'
    assert 'problem_statement' in debate['policy_config']
    assert debate['policy_config']['problem_statement'] == "What features should we prioritize in Q1?"
    assert debate['policy_config']['timebox_minutes'] == 30


def test_debate_setup_with_agent_references():
    """Test POST /debates/setup with references to existing agents"""
    from src.debate_service import DebateService
    workspace_id = '00000000-0000-0000-0000-000000000101'
    
    # Create a persistent agent first
    agent_response = client.post("/agents", json={
        "workspace_id": workspace_id,
        "name": "Persistent PM",
        "system_prompt": "You are a persistent product manager.",
        "model_id": "anthropic/claude-3.5-sonnet",
        "agent_model_config": {}
    })
    agent_id = agent_response.json()['agent_id']
    
    # Create debate referencing this agent
    response = client.post("/debates/setup", json={
        "workspace_id": workspace_id,
        "title": "Strategy Session",
        "problem_statement": "Should we pivot our product strategy?",
        "participants": [
            {"agent_id": agent_id}
        ],
        "materials": []
    })
    
    assert response.status_code == 201
    data = response.json()
    
    assert len(data['participant_ids']) == 1
    assert len(data['material_ids']) == 0


def test_debate_setup_participant_limit():
    """Test that debate setup enforces participant limits"""
    workspace_id = '00000000-0000-0000-0000-000000000101'
    
    # Try to create with 9 participants (max is 8)
    participants = [
        {
            "name": f"Agent {i}",
            "system_prompt": "Test",
            "model_id": "anthropic/claude-3.5-sonnet"
        }
        for i in range(9)
    ]
    
    response = client.post("/debates/setup", json={
        "workspace_id": workspace_id,
        "title": "Too Many Participants",
        "problem_statement": "Test",
        "participants": participants,
        "materials": []
    })
    
    assert response.status_code == 400
    assert 'maximum' in response.json()['detail'].lower()


def test_debate_setup_requires_at_least_one_participant():
    """Test that debate setup requires at least one participant"""
    workspace_id = '00000000-0000-0000-0000-000000000101'
    
    response = client.post("/debates/setup", json={
        "workspace_id": workspace_id,
        "title": "No Participants",
        "problem_statement": "Test",
        "participants": [],
        "materials": []
    })
    
    assert response.status_code == 400
    assert 'at least 1' in response.json()['detail'].lower()


def test_debate_setup_inline_participant_validation():
    """Test that inline participants require name, system_prompt, model_id"""
    workspace_id = '00000000-0000-0000-0000-000000000101'
    
    response = client.post("/debates/setup", json={
        "workspace_id": workspace_id,
        "title": "Invalid Participant",
        "problem_statement": "Test",
        "participants": [
            {
                "name": "Agent",
                # Missing system_prompt and model_id
            }
        ],
        "materials": []
    })
    
    assert response.status_code == 400
    assert 'require' in response.json()['detail'].lower()
