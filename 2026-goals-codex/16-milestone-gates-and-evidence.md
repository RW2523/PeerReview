# 16 - Milestone Gates and Evidence

Date: 2026-02-06  
Purpose: enforce hard Yes/No checkpoints so progress is demo-able, testable, and not based on narrative status.

## Gate Policy
- A milestone is complete only if all gate checks are `Yes`.
- Each gate must include:
- positive proof (command output, API response, or UI recording)
- one negative test (expected failure path)
- No advancement to next milestone when any gate check is `No`.

## M1 Gate - Debate in a Box API
Goal: API can run a 5-turn debate and return machine-usable outputs.

### Required Checks (Yes/No)
- `POST /debates/run` accepts: problem statement, 3 personas/agents, OpenRouter key.
- Debate executes 5 turns in deterministic round-robin order.
- Response includes:
- final summary
- minutes of meeting (MoM)
- action items
- full event history for all turns
- Event history persists to DB ledger (`debate_events` equivalent).
- Invalid/missing OpenRouter key is rejected with clear error response.

### Required Evidence
- curl/postman request + response JSON captured.
- DB query output showing persisted event rows for the same debate ID.
- one short demo clip or terminal transcript of success path.

### Negative Test
- Run with missing OpenRouter key and confirm non-2xx response + structured error.

## M2 Gate - Realtime Discussion Control
Goal: user can observe and control live debate in real time.

### Required Checks (Yes/No)
- User can see live token/message stream in UI (SSE/WebSocket).
- User can pause and resume the debate.
- User can intervene and tag specific agents during the session.
- User can end meeting manually at any time.
- End action always emits:
- auto summary
- MoM
- action items

### Required Evidence
- UI recording showing start -> live stream -> pause -> intervene/tag -> resume -> end.
- event stream snapshot proving correct event types and order.

### Negative Test
- Attempt intervention while debate is ended; verify action is blocked with clear error.

## M3 Gate - Agent Continuity and Known-Only Memory
Goal: imported agents answer from learned facts only, without fabricated assumptions.

### Required Checks (Yes/No)
- User can import agent from prior meeting into a new meeting.
- Agent responses can cite prior learned facts from stored memory.
- When asked about unknown information, agent explicitly states unknown.
- No uncited architectural/product claims are emitted in known-only mode.

### Required Evidence
- two linked meeting IDs showing agent import across meetings.
- sample Q/A transcript with citations to stored memory entries.
- retrieval/debug log for one answer (what context was loaded).

### Negative Test
- Ask imported agent about a fact absent from memory; verify unknown response and no hallucinated detail.

## M4 Gate - Persona Lifecycle
Goal: persona setup is usable, transparent, and safe before meeting start.

### Required Checks (Yes/No)
- User can create persona from preset template.
- User can auto-generate persona from minimal input (AI-assisted draft).
- User can preview exact prompt/config before launch.
- User can edit prompt/config before launch.
- Prompt/schema validation blocks invalid persona configs.

### Required Evidence
- UI recording: template -> preview -> edit -> validate -> launch.
- stored persona config snapshot (redacted if needed).

### Negative Test
- Submit invalid persona config; verify launch is blocked and validation errors are shown.

## M5 Gate - Voice/Text Unified Engine
Goal: voice uses the same core debate pipeline as text.

### Required Checks (Yes/No)
- Voice transcript events enter same event schema/state machine as text.
- Debate orchestration behavior is equivalent for voice and text inputs.
- End outputs (summary, MoM, action items) are identical in structure for both modes.
- Session can be time-bounded and ended manually in voice mode.

### Required Evidence
- one text-run and one voice-run trace with matching state transition classes.
- payload examples for `voice_transcript_partial` and `voice_transcript_final`.

### Negative Test
- Feed malformed voice transcript payload; verify schema/state validation rejects it.

## Evidence Checklist Template (Copy Per Milestone)
- Milestone ID:
- Gate status: `Yes` / `No`
- Positive proof links:
- Negative test proof:
- Known limitations accepted:
- Reviewer sign-off:
- Date:

## Execution Rule
- Treat gates as release blockers, not documentation.
- If a gate fails, create a focused fix ticket and re-run the same gate before any new scope.
