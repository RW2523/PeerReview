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

// ============================================================================
// DEBATES DOMAIN (lines 24-220)
// TODO: Extract to api/debates.ts
// ============================================================================

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

export async function triggerNextTurn(debateId: string, openrouterKey: string): Promise<any> {
  const headers = await getAuthHeaders() as Record<string, string>;
  headers['X-OpenRouter-Key'] = openrouterKey;
  
  const response = await fetch(`${API_URL}/debates/${debateId}/turn/next`, {
    method: 'POST',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to trigger next turn: ${response.statusText}`);
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
// ============================================================================
// AGENTS & SETUP DOMAIN (lines 224-320)
// TODO: Extract to api/agents.ts and api/setup.ts
// ============================================================================

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
// ============================================================================
// OPENROUTER DOMAIN (lines 322-405)
// TODO: Extract to api/openrouter.ts
// ============================================================================

export interface OpenRouterAccountResponse {
  key?: {
    label?: string;
    usage?: number;
    limit?: number | null;
    rate_limit?: any;
    is_free_tier?: boolean;
    is_valid?: boolean;
    validated_via?: string;
  };
  credits?: {
    total_credits?: number | null;
    total_usage?: number | null;
    balance?: number | null;
  } | null;
  models_available?: number;
  has_management_key?: boolean;
  note?: string | null;
}

export interface OpenRouterModelListResponse {
  models: Array<{
    id: string;
    name: string;
    context_length?: number;
    pricing?: any;
  }>;
}

export async function listOpenRouterModels(openrouterKey: string): Promise<OpenRouterModelListResponse> {
  const response = await fetch(`${API_URL}/openrouter/models`, {
    method: 'GET',
    headers: {
      'X-OpenRouter-Key': openrouterKey,
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch models: ${response.statusText}`);
  }
  
  return response.json();
}

export async function getOpenRouterAccount(
  openrouterKey: string,
  managementKey?: string | null
): Promise<OpenRouterAccountResponse> {
  const headers: Record<string, string> = {
    'X-OpenRouter-Key': openrouterKey,
  };
  
  if (managementKey) {
    headers['X-OpenRouter-Management-Key'] = managementKey;
  }
  
  const response = await fetch(`${API_URL}/openrouter/account`, {
    method: 'GET',
    headers,
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

// Materials upload and status
// ============================================================================
// MATERIALS DOMAIN (lines 430-510)  
// TODO: Extract to api/materials.ts
// ============================================================================

export interface MaterialUploadResponse {
  material_ids: string[];
  job_ids: string[];
  total_files: number;
}

export interface MaterialStatus {
  material_id: string;
  title: string;
  kind: string;
  file_size_bytes?: number;
  file_mime_type?: string;
  processed_status: string;
  processing_metadata: Record<string, any>;
  created_at: string;
  processing_started_at?: string;
  processing_completed_at?: string;
}

export interface MaterialsStatusResponse {
  debate_id: string;
  total_materials: number;
  status_summary: Record<string, number>;
  materials: MaterialStatus[];
}

export async function uploadMaterials(
  debateId: string,
  files: File[]
): Promise<MaterialUploadResponse> {
  const token = await getAccessToken();
  const formData = new FormData();
  
  files.forEach(file => {
    formData.append('files', file);
  });
  
  const response = await fetch(`${API_URL}/debates/${debateId}/materials/upload`, {
    method: 'POST',
    headers: {
      'Authorization': token ? `Bearer ${token}` : '',
    },
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to upload materials: ${response.statusText}`);
  }
  
  return response.json();
}

export async function getMaterialsStatus(debateId: string): Promise<MaterialsStatusResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/materials/status`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to get materials status: ${response.statusText}`);
  }
  
  return response.json();
}

export async function retryMaterial(debateId: string, materialId: string): Promise<any> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/materials/retry`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ material_id: materialId }),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to retry material: ${response.statusText}`);
  }
  
  return response.json();
}

// Memory Import API

// ============================================================================
// MEMORY DOMAIN (lines 513-670)
// TODO: Extract to api/memory.ts  
// ============================================================================

export interface ImportableDebate {
  debate_id: string;
  title: string;
  state: string;
  created_at: string;
  ended_at?: string | null;
  chunk_count: number;
  material_count: number;
  artifact_count: number;
  participant_count: number;
}

export interface ImportableSourcesResponse {
  workspace_id: string;
  debates: ImportableDebate[];
  total_count: number;
}

export interface MemoryPreviewChunk {
  source_type: string;
  title: string;
  chunk_count: number;
  last_updated: string;
}

export interface MemoryPreviewResponse {
  source_debate_id: string;
  source_title: string;
  total_chunks: number;
  breakdown: MemoryPreviewChunk[];
  date_range: {
    start?: string | null;
    end?: string | null;
  };
}

export interface MemoryImportRequest {
  source_debate_ids: string[];
  source_type?: 'debate_full' | 'materials_only';
  scope?: 'all_agents' | 'specific_agents';
  participant_ids?: string[];
  metadata?: Record<string, any>;
}

export interface MemoryImportResponse {
  debate_id: string;
  grants_created: number;
  grant_ids: string[];
}

export interface MemoryGrant {
  grant_id: string;
  source_debate_id?: string | null;
  source_debate_title?: string | null;
  source_artifact_id?: string | null;
  source_artifact_title?: string | null;
  source_type: string;
  scope: string;
  allowed_participant_ids?: string[] | null;
  granted_by: string;
  granted_at: string;
  expires_at?: string | null;
  metadata: Record<string, any>;
}

export interface MemoryGrantsResponse {
  debate_id: string;
  grants: MemoryGrant[];
  total_count: number;
}

export async function listImportableMemorySources(
  workspaceId: string,
  limit?: number
): Promise<ImportableSourcesResponse> {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams();
  if (limit) params.append('limit', limit.toString());
  
  const response = await fetch(`${API_URL}/workspaces/${workspaceId}/memory/importable?${params}`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to list importable sources: ${response.statusText}`);
  }
  
  return response.json();
}

export async function previewMemoryImport(
  debateId: string,
  sourceDebateId: string
): Promise<MemoryPreviewResponse> {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams({ source_debate_id: sourceDebateId });
  
  const response = await fetch(`${API_URL}/debates/${debateId}/memory/preview?${params}`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to preview memory import: ${response.statusText}`);
  }
  
  return response.json();
}

export async function importMemory(
  debateId: string,
  request: MemoryImportRequest
): Promise<MemoryImportResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/memory/import`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to import memory: ${response.statusText} - ${errorText}`);
  }
  
  return response.json();
}

export async function listMemoryGrants(debateId: string): Promise<MemoryGrantsResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/memory/grants`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to list memory grants: ${response.statusText}`);
  }
  
  return response.json();
}

export async function revokeMemoryGrant(debateId: string, grantId: string): Promise<any> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/memory/grants/${grantId}`, {
    method: 'DELETE',
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to revoke memory grant: ${response.statusText}`);
  }
  
  return response.json();
}

// Preflight API

// ============================================================================
// PREFLIGHT DOMAIN (lines 672-785)
// TODO: Extract to api/preflight.ts
// ============================================================================

export interface ParticipantRunStatus {
  participant_run_id: string;
  participant_id: string;
  agent_id?: string;
  status: 'queued' | 'running' | 'success' | 'failed' | 'skipped';
  started_at?: string;
  completed_at?: string;
  error?: string;
  skip_reason?: string;
  prep_pack_knowledge_id?: string;
  metadata?: Record<string, any>;
}

export interface PreflightStartResponse {
  run_id: string;
  debate_id: string;
  status: string;
  participant_count: number;
  participant_runs: Array<{
    participant_run_id: string;
    participant_id: string;
    agent_id?: string;
    status: string;
  }>;
}

export interface PreflightStatusResponse {
  run_id: string;
  debate_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  participant_runs: ParticipantRunStatus[];
}

export interface PreflightActionResponse {
  participant_run_id: string;
  participant_id: string;
  status: string;
  message: string;
}

export async function startPreflight(debateId: string): Promise<PreflightStartResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/preflight/start`, {
    method: 'POST',
    headers,
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to start preflight: ${response.statusText} - ${errorText}`);
  }
  
  return response.json();
}

export async function getPreflightStatus(debateId: string): Promise<PreflightStatusResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/preflight/status`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to get preflight status: ${response.statusText} - ${errorText}`);
  }
  
  return response.json();
}

export async function retryPreflightParticipant(
  debateId: string,
  participantId: string
): Promise<PreflightActionResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/preflight/retry`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ participant_id: participantId }),
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to retry preflight: ${response.statusText} - ${errorText}`);
  }
  
  return response.json();
}

export async function skipPreflightParticipant(
  debateId: string,
  participantId: string,
  reason: string
): Promise<PreflightActionResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/preflight/skip`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ participant_id: participantId, reason }),
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to skip preflight: ${response.statusText} - ${errorText}`);
  }
  
  return response.json();
}

// ============================================================================
// Workspace Settings
// ============================================================================

// ============================================================================
// WORKSPACE SETTINGS DOMAIN (lines 789-835)
// TODO: Extract to api/workspace.ts
// ============================================================================

export interface WorkspaceModelsRequest {
  embeddings_model_id: string;
  ocr_model_id: string;
}

export interface WorkspaceModelsResponse {
  workspace_id: string;
  embeddings_model_id: string;
  ocr_model_id: string;
  updated_at: string;
}

export async function getWorkspaceModels(workspaceId: string): Promise<WorkspaceModelsResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/workspaces/${workspaceId}/settings/models`, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to get workspace models: ${response.statusText} - ${errorText}`);
  }
  
  return response.json();
}

export async function updateWorkspaceModels(
  workspaceId: string,
  models: WorkspaceModelsRequest
): Promise<WorkspaceModelsResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/workspaces/${workspaceId}/settings/models`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(models),
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to update workspace models: ${response.statusText} - ${errorText}`);
  }
  
  return response.json();
}

// ============================================================================
// Presence & Typing (TICKET-14)
// ============================================================================

// ============================================================================
// PRESENCE DOMAIN (lines 839-878)
// TODO: Extract to api/presence.ts
// ============================================================================

export interface PresenceResponse {
  event_id: string;
  debate_id: string;
  event_type: string;
  sequence_number: number;
  created_at: string;
}

export async function joinPresence(debateId: string, participantId?: string, metadata: any = {}): Promise<PresenceResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/presence/join`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ participant_id: participantId, metadata })
  });
  if (!response.ok) throw new Error(`Failed to join presence: ${response.statusText}`);
  return response.json();
}

export async function leavePresence(debateId: string, participantId?: string): Promise<PresenceResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/presence/leave`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ participant_id: participantId })
  });
  if (!response.ok) throw new Error(`Failed to leave presence: ${response.statusText}`);
  return response.json();
}

export async function signalTyping(debateId: string, participantId?: string, targetParticipantId?: string): Promise<PresenceResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/debates/${debateId}/typing`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ participant_id: participantId, target_participant_id: targetParticipantId })
  });
  if (!response.ok) throw new Error(`Failed to signal typing: ${response.statusText}`);
  return response.json();
}
