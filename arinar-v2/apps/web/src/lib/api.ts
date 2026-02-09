/**
 * API client for Arinar backend
 */
import { getAccessToken } from './supabase';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeaders(): Promise<HeadersInit> {
  const token = await getAccessToken();
  
  if (token) {
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }
  
  // No token available
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
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ workspace_id: workspaceId, title }),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to create debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function getDebate(debateId: string): Promise<any> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to get debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function startDebate(debateId: string): Promise<DebateResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/start`, {
    method: 'POST',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to start debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function pauseDebate(debateId: string): Promise<DebateResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/pause`, {
    method: 'POST',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to pause debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function resumeDebate(debateId: string): Promise<DebateResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/resume`, {
    method: 'POST',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to resume debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function endDebate(debateId: string): Promise<DebateResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/end`, {
    method: 'POST',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to end debate: ${response.statusText}`);
  }
  
  return response.json();
}

export async function intervene(debateId: string, request: InterventionRequest): Promise<any> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/intervene`, {
    method: 'POST',
    headers,
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

// M3 Summary endpoints
export interface SummarizeRequest {
  openrouter_api_key: string;
  model_id?: string;
}

export interface ActionItem {
  description: string;
  owner: string;
  priority: 'high' | 'medium' | 'low';
}

export interface SummaryResponse {
  output_id: string;
  debate_id: string;
  summary: string;
  minutes: string;
  action_items: ActionItem[];
  generated_at: string;
  model_used?: string;
}

export async function generateSummary(
  debateId: string,
  request: SummarizeRequest,
  openrouterKey: string
): Promise<SummaryResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/summarize`, {
    method: 'POST',
    headers: {
      ...headers,
      'X-OpenRouter-Key': openrouterKey,
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to generate summary: ${response.statusText}`);
  }
  
  return response.json();
}

export async function getSummary(debateId: string): Promise<SummaryResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/summary`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Summary not generated yet');
    }
    throw new Error(`Failed to get summary: ${response.statusText}`);
  }
  
  return response.json();
}

// M4 Meeting Setup endpoints
export interface AgentTemplate {
  template_id: string;
  label: string;
  role_title: string;
  category: string;  // e.g. "Product", "Engineering", "Design", "Business", "Wildcards"
  character?: string;  // e.g. "Visionary - Jobs-inspired", "Pragmatic - Data-driven"
  system_prompt: string;
  model_id: string;
  model_config: Record<string, any>;
}

export interface Agent {
  agent_id: string;
  workspace_id: string;
  name: string;
  role_description?: string;
  system_prompt: string;
  model_id: string;
  model_config: Record<string, any>;
  created_at: string;
}

export interface SetupParticipant {
  agent_id?: string;
  name?: string;
  role_description?: string;
  system_prompt?: string;
  model_id?: string;
  model_config?: Record<string, any>;
}

export interface SetupMaterial {
  kind: 'text' | 'link' | 'file_placeholder';
  title?: string;
  body_text?: string;
  url?: string;
}

export interface DebateSetupRequest {
  workspace_id: string;
  title: string;
  problem_statement: string;
  timebox_minutes?: number;
  participants: SetupParticipant[];
  materials?: SetupMaterial[];
}

export interface DebateSetupResponse {
  debate_id: string;
  participant_ids: string[];
  material_ids: string[];
}

export async function listAgentTemplates(): Promise<AgentTemplate[]> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/agent-templates`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch templates: ${response.statusText}`);
  }
  
  return response.json();
}

export async function listAgents(workspaceId: string): Promise<Agent[]> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/agents?workspace_id=${workspaceId}`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch agents: ${response.statusText}`);
  }
  
  return response.json();
}

export async function setupDebate(request: DebateSetupRequest): Promise<DebateSetupResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/setup`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to setup debate: ${response.statusText}`);
  }
  
  return response.json();
}

// OpenRouter account info
export interface OpenRouterAccountResponse {
  key?: {
    label?: string;
    usage?: number;
    limit?: number | null;
    rate_limit?: any;
    is_free_tier?: boolean;
  };
  credits?: {
    total_credits?: number;
    total_usage?: number;
    balance?: number;
  } | null;
  note?: string | null;
}

export async function getOpenRouterAccount(openrouterKey: string): Promise<OpenRouterAccountResponse> {
  const response = await fetch(`${API_URL}/openrouter/account`, {
    method: 'GET',
    headers: {
      'X-OpenRouter-Key': openrouterKey,
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch account info: ${response.statusText}`);
  }
  
  return response.json();
}

// Debates list
export interface DebateListItem {
  debate_id: string;
  workspace_id: string;
  title: string;
  state: string;
  created_at: string;
  updated_at?: string;
  started_at?: string;
  ended_at?: string;
}

export interface DebateListResponse {
  items: DebateListItem[];
  next_cursor?: string | null;
}

export async function listDebates(
  workspaceId: string,
  limit?: number,
  cursor?: string
): Promise<DebateListResponse> {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams({ workspace_id: workspaceId });
  if (limit) params.append('limit', limit.toString());
  if (cursor) params.append('cursor', cursor);
  
  const response = await fetch(`${API_URL}/debates?${params}`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to list debates: ${response.statusText}`);
  }
  
  return response.json();
}
