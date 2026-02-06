/**
 * API client for Arinar backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const AUTH_MODE = process.env.NEXT_PUBLIC_AUTH_MODE || 'production';
const TEST_TOKEN = process.env.NEXT_PUBLIC_TEST_TOKEN || '';

function getAuthHeaders(): HeadersInit {
  // Phase 4A: Use test token for development
  // Phase 4B+: Replace with real Supabase session token
  if (AUTH_MODE === 'development' && TEST_TOKEN) {
    return {
      'Authorization': `Bearer ${TEST_TOKEN}`,
      'Content-Type': 'application/json',
    };
  }
  
  // Production mode would get token from Supabase session
  return {
    'Content-Type': 'application/json',
  };
}

export interface DebateResponse {
  debate_id: string;
  workspace_id: string;
  title: string;
  state: string;
  created_at: string;
}

export interface InterventionRequest {
  message: string;
  tagged_agents?: string[];
}

export async function createDebate(workspaceId: string, title: string): Promise<DebateResponse> {
  const response = await fetch(`${API_URL}/debates`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ workspace_id: workspaceId, title }),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to create debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function startDebate(debateId: string): Promise<DebateResponse> {
  const response = await fetch(`${API_URL}/debates/${debateId}/start`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to start debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function pauseDebate(debateId: string): Promise<DebateResponse> {
  const response = await fetch(`${API_URL}/debates/${debateId}/pause`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to pause debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function resumeDebate(debateId: string): Promise<DebateResponse> {
  const response = await fetch(`${API_URL}/debates/${debateId}/resume`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to resume debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function endDebate(debateId: string): Promise<DebateResponse> {
  const response = await fetch(`${API_URL}/debates/${debateId}/end`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to end debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function intervene(debateId: string, request: InterventionRequest): Promise<any> {
  const response = await fetch(`${API_URL}/debates/${debateId}/intervene`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to intervene: ${response.statusText}`);
  }
  
  return response.json();
}

export function getStreamUrl(debateId: string, since?: number): string {
  const url = new URL(`${API_URL}/debates/${debateId}/events/stream`);
  if (since !== undefined) {
    url.searchParams.set('since', since.toString());
  }
  return url.toString();
}
