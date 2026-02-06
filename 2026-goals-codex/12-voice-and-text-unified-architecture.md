# Voice and Text Unified Architecture (2026)

## Purpose
Design once for both:
- text-first debates now,
- voice-call debates later,
without splitting orchestration, memory, or compliance models.

## 1) Unified Conversation Principle
All interactions become normalized events in one ledger:
- text message,
- voice transcript segment,
- intervention,
- tool call,
- research result,
- decision output.

Text and voice are only different input/output modalities. Core debate logic remains shared.

## 2) Session Modalities
Each debate session has:
- `modality`: `text_only|voice_only|hybrid`
- `primary_channel`: `chat|call`
- `recording_policy`: `off|transcript_only|audio_and_transcript`

## 3) Voice Pipeline (Future)
1. User joins voice room.
2. Audio stream -> STT service.
3. Transcript chunks -> event ledger (`voice_transcript_event`).
4. Debate orchestrator processes transcript as normal message input.
5. Agent response generated through standard model path.
6. Response rendered as text and optionally TTS audio.

## 4) Shared Event Contract
New event types for voice:
- `voice_stream_started`
- `voice_transcript_partial`
- `voice_transcript_final`
- `voice_tts_started`
- `voice_tts_completed`
- `voice_stream_ended`

All must include:
- `session_id`
- `speaker_id`
- `turn_id`
- `timestamp`
- `trace_id`

## 5) MCP and Tool Calling Architecture
Agents should support controlled tool usage in future through a dedicated gateway.

### Components
- `ToolGateway`: central policy and execution layer for tool calls.
- `MCPAdapter`: connects to approved MCP servers.
- `ToolRegistry`: approved tools, capabilities, schemas, risk classes.

### Flow
1. Agent emits `tool_call_request`.
2. Policy engine validates:
- agent/tool permission,
- workspace policy,
- risk class,
- optional human approval.
3. Gateway executes tool:
- internal tool, or
- MCP server tool via adapter.
4. Gateway returns `tool_call_result`.
5. Result is persisted with provenance and fed into context packet.

### Core rules
- No direct agent-to-tool execution.
- All tool calls go through gateway.
- All tool inputs/outputs are audit logged.

## 6) MCP Readiness Requirements
- MCP server allowlist per workspace.
- Tool schema validation before execution.
- Timeout/retry/circuit breaker controls.
- Secret isolation per tool/server.
- Signed audit trail for MCP calls.

## 7) Memory and Modality
Memory stores:
- canonical transcript text as primary knowledge artifact,
- optional audio references,
- tool call outputs as evidence-linked knowledge units.

This ensures continuity regardless of whether prior session was text or voice.

## 8) UX Requirements
### Debate creation
- User chooses `text`, `voice`, or `hybrid`.
- User chooses whether agents can use tools/MCP.

### Live workspace
- Same Slack-like timeline for all events.
- Voice sessions show transcript in real time.
- Tool calls show expandable cards with status and outputs.

## 9) Compliance and Safety
- Voice sessions inherit same retention and deletion policies.
- Transcript redaction pipeline for sensitive entities.
- Tool/MCP calls subject to same tenant boundaries as memory/research.
- Human can stop voice session and tool execution immediately.

## 10) Rollout Plan
1. `V1`: text-only + no MCP tool calling by default.
2. `V1.5`: hybrid mode with transcript-first voice support.
3. `V2`: controlled MCP tool calling for selected enterprise tenants.
