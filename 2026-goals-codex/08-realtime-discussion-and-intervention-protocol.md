# Realtime Discussion and Intervention Protocol (2026)

## Purpose
Define how multi-agent realtime discussion works in production, including agent tags, interventions, turn queueing, and state transitions.

## 1) Core Entities
- `DebateSession`
- `ParticipantAgent`
- `HumanUser`
- `MessageEvent`
- `InterventionEvent`
- `PreTurnNudgeEvent`
- `TurnQueue`
- `DecisionState`

## 2) Session States
- `draft`
- `preflight`
- `live`
- `paused`
- `synthesis`
- `closed`
- `archived`

Allowed transitions:
- `draft -> preflight -> live`
- `live <-> paused`
- `live -> synthesis -> closed`
- `closed -> archived`

## 3) Message Event Types
- `agent_message`
- `human_message`
- `agent_question`
- `agent_rebuttal`
- `intervention`
- `evidence_request`
- `evidence_response`
- `summary_update`
- `decision_candidate`
- `decision_finalized`
- `pre_turn_nudge`
- `nudge_approved`
- `nudge_rejected`
- `research_request`
- `research_result`
- `research_denied`
- `knowledge_imported`
- `knowledge_rejected`
- `unknown_response`
- `tool_call_request`
- `tool_call_result`
- `tool_call_denied`
- `voice_transcript_partial`
- `voice_transcript_final`
- `voice_tts_started`
- `voice_tts_completed`

Each event envelope:
- `event_id`
- `debate_id`
- `event_type`
- `sender_type` (`agent|human|system`)
- `sender_id`
- `mentions[]`
- `thread_id` (optional)
- `content`
- `citation_refs[]`
- `priority`
- `created_at`

## 4) Response Style and Verbosity Policy
Default behavior:
- Agents should auto-select concise vs detailed response based on task complexity.
- Slack-style baseline favors short, high-signal responses first.

Response envelope:
- `answer_summary` (required, short)
- `detail_block` (optional, expandable)
- `citations` (required when factual claims are made)

Controls:
- User can override any turn with `brief`, `standard`, `deep_dive`.
- Host can enforce max token cap per mode.

No-assumptions rule:
- In strict mode, outgoing agent claims must map to known source-backed knowledge.
- If no supported knowledge exists, emit `unknown_response` instead of speculative answer.

## 5) Internet Research Protocol (Policy Controlled)
Default:
- Internet access is `off` unless enabled by workspace/debate policy.

When enabled:
1. Agent emits `research_request` with query + justification.
2. Policy engine checks:
- agent permission,
- domain allowlist/denylist,
- budget and rate limits,
- optional human approval requirement.
3. Backend research gateway executes approved fetch/search.
4. Gateway returns `research_result` with normalized snippets and source URLs.
5. If blocked, emit `research_denied` with policy reason.

Rules:
- No direct model browsing to open internet.
- All external facts used in responses must include source references.
- All research calls are audit logged.

## 5A) Tool Calling and MCP Protocol (Future)
Default:
- Tool calling is `off` unless explicitly enabled by policy.

When enabled:
1. Agent emits `tool_call_request` with tool name, args, and justification.
2. Policy engine validates permission, risk class, and approval requirements.
3. Tool gateway executes approved call (internal tool or MCP tool).
4. Emit `tool_call_result` with normalized output and provenance.
5. If blocked, emit `tool_call_denied`.

Rules:
- No direct agent-to-tool execution path.
- All tool/MCP calls are audited with input/output metadata.
- Tool results can be cited in subsequent agent responses.

## 6) Agent Tagging Semantics
### Syntax
- `@RoleName` in composer and agent messages.

### Behavior
- Mentioned agents receive a targeted task.
- Mentioned task is inserted into queue with priority boost.
- Agent response should explicitly reference tagged question.

### Failure handling
- If tagged agent is blocked (model error/rate limit):
  - emit `agent_unavailable`,
  - fallback to alternate model if allowed by policy,
  - otherwise notify user and keep question open.

## 7) Pre-turn Nudge Protocol
Purpose:
- Let agents act human-like by asking host to speak before their scheduled turn when relevant.

Nudge payload:
- `agent_id`
- `reason` (`urgent_correction|new_evidence|direct_challenge|critical_risk`)
- `target_message_id` (optional)
- `proposed_response_brief`

Host arbitration:
1. Agent emits `pre_turn_nudge`.
2. Host evaluates queue impact and policy.
3. Host emits `nudge_approved` or `nudge_rejected`.
4. If approved, task is inserted at boosted priority.

Latency target:
- Nudge arbitration path should be in-memory and near real-time.
- Target decision path: `100-400ms` in normal load.

## 8) Turn Queue Policy
Default strategy: `hybrid priority queue`

Priority tiers:
1. `P0` user intervention
2. `P1` direct mention response
3. `P2` scheduled turn order
4. `P3` optional follow-up

Tie-breakers:
- oldest waiting task first,
- fairness guard (prevent same agent monopolizing turns),
- unresolved objection bonus.

## 9) Intervention Protocol
### Triggers
- Manual user trigger (`Intervene` button).
- Policy trigger (unsafe claim, missing citation, contradiction spike).

### Intervention payload
- `intent` (`clarify|challenge|re_scope|request_evidence|decision_check`)
- `target_agents[]`
- `question_or_instruction`
- `blocking` (if true, pauses normal queue until addressed)

### Execution
1. Emit `intervention` event.
2. Insert high-priority tasks for targets.
3. Pause or continue queue based on `blocking`.
4. Require explicit response marker from each target agent.

## 10) Timebox and Meeting End Protocol
Timebox:
- Session tracks `meeting_timebox_minutes`.
- Host emits warning events at defined checkpoints.

End conditions:
- user manual end (`End Now`) always allowed,
- configured timeout behavior (`host_suggest|hard_stop|user_only`),
- policy stop (admin/compliance) if needed.

Post-end automation:
1. Lock queue for new debate turns.
2. Run synthesis pass.
3. Generate:
- auto summary,
- minutes of meeting,
- action items with owners/timelines,
- unresolved questions.
4. Persist and publish output package.

## 11) Realtime Transport Strategy
- Use SSE for token streaming from model responses.
- Use pub/sub channel for room-wide state and event fan-out.
- Client state merges:
  - streamed token chunks into message body,
  - room events into feed/timeline,
  - queue/state updates into side panel.

Voice extension:
- Voice transcripts are normalized to standard message events.
- TTS lifecycle events are emitted for playback synchronization.

## 12) Consistency and Idempotency
- Every event has a unique `event_id`.
- Server enforces idempotent append for retries.
- Projections (`state`, `queue`) rebuilt from immutable event ledger.
- Client can replay from last received `sequence_number`.

## 13) Human UX Rules
- User can always:
  - pause,
  - ask direct question,
  - request evidence,
  - override turn order temporarily.
- System must always show:
  - who is speaking,
  - who is queued next,
  - which questions are unresolved.

## 14) Quality Gates Before Decision Close
Cannot finalize decision unless:
- critical tagged questions are answered,
- required roles have at least one substantive contribution,
- citations exist for high-impact claims,
- unknown responses are resolved or explicitly accepted by user,
- user confirms closure.

## 15) Telemetry
Track:
- intervention frequency,
- nudge request volume and approval ratio,
- research request/approval/deny rates,
- response latency by agent/model,
- unresolved question count,
- evidence coverage ratio,
- decision confidence trend.

## 16) Security and Enterprise
- Tenant-scoped channels and event filters.
- Audit logs for all intervention events and role/model changes.
- Audit logs for all internet research requests and fetched domains.
- Redaction policy for sensitive fields in event payloads.
- Retention policy applied per workspace and data class.
