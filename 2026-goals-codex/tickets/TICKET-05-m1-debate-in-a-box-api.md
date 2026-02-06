# TICKET-05: M1 Debate-In-A-Box API (Core Loop First)

## Status
- `ready`

## Objective
Ship a single working backend loop that proves core product value:
- given a problem statement + 3 agents + OpenRouter BYOK,
- run a 5-turn round-robin debate,
- persist event history,
- return summary output JSON.

No advanced UI/orchestration scope in this ticket.

## Scope
In scope:
- minimal API endpoint to run one complete debate loop.
- OpenRouter request path and provider abstraction (OpenRouter-only).
- deterministic 5-turn round-robin orchestration.
- event ledger persistence in existing DB schema.
- end payload with summary, minutes, and action items.
- tests for happy path + key failure paths.

Out of scope:
- realtime SSE/WebSocket.
- pause/resume/intervention controls.
- voice mode.
- full memory fabric retrieval logic.

## Mandatory Standards
Follow:
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/15-engineering-standards-and-anti-chaos-rules.md`
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/16-milestone-gates-and-evidence.md`
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/17-decisions-log.md`
- `/Users/pv/Downloads/arinar-6-IPSS-V5/arinar-v2/WORKSPACE-MAP.md`
- Model-provider policy: OpenRouter-only. Do not integrate direct OpenAI/Anthropic/Google provider SDK usage.

## Prerequisite
- Ticket-03.1 and Ticket-04 passed.

## Cursor Instructions
1. Work only inside `arinar-v2/`.
2. Implement minimal API service skeleton in `apps/api/` (FastAPI baseline per workspace map).
3. Add endpoint:
- `POST /debates/run`
4. Request contract for endpoint should include:
- `problem_statement` (string)
- `agents` (exactly 3 for M1): `name`, `role`, `model_id`
- `openrouter_api_key` (string, request-time BYOK)
- optional `debate_title`
5. Behavior:
- validate input.
- run 5-turn round-robin across the 3 agents.
- each turn generates one agent message via OpenRouter.
- store debate, participants, and events in DB ledger tables.
- generate final outputs:
  - `summary`
  - `minutes_of_meeting`
  - `action_items` (array)
- return JSON with:
  - `debate_id`
  - `status`
  - `outputs` (summary/minutes/action_items)
  - `event_history` (ordered events)
6. Add simple OpenRouter client abstraction (single module) with timeout/retry guardrails.
7. Add/update contracts:
- OpenAPI update for `POST /debates/run`
- generated types in `packages/contracts/src/generated/`
- event compatibility with existing schemas
8. Tests required:
- happy path (5-turn completes and returns expected shape).
- missing/invalid OpenRouter key returns clear non-2xx error.
- DB persistence check for created debate + events.
- deterministic turn-order assertion.
9. Add runbook:
- `docs/runbooks/m1-debate-in-a-box.md`
- include local run, example request, expected response, troubleshooting.

## Founder Action Required
- None blocking for local.
- Later provide production/staging OpenRouter policy (allowed model list + rate/spend caps).

## Deliverables
- working `POST /debates/run` implementation.
- contract updates + generated types.
- tests proving core loop and failure handling.
- runbook with reproducible local demo steps.

## Validation Checklist
- endpoint exists and is documented.
- round-robin produces exactly 5 turns.
- output payload includes summary, minutes, action items.
- debate and event rows persist in DB.
- invalid OpenRouter key path is handled cleanly.

## Test/Verify Commands
Run and include output summary:
- `make verify`
- API unit/integration tests for `POST /debates/run`
- one local smoke run (request + response)
- one negative run (invalid key) proving expected failure

## Reporting (Mandatory)
Before completion:
1. create report file:
- `bash scripts/new_ticket_report.sh TICKET-05`
2. fill report with command evidence using template.
3. update:
- `/Users/pv/Downloads/arinar-6-IPSS-V5/arinar-v2/reports/tickets/INDEX.md`
4. chat output must contain only:
- report path
- final status
- blockers

## Definition of Done
- M1 gate is passable from command evidence:
- Can run one 5-turn debate through API and get summary + event history JSON.
- key failure path validated.
- ready to begin M2 realtime/control ticket.

