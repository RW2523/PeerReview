# TICKET-06: M2 Realtime Controls, Live Feed, and Supabase Auth Baseline

## Status
- `ready`

## Objective
Deliver the M2 control loop with auth foundations:
- user can watch a live debate stream,
- pause/resume,
- intervene by tagging agent(s),
- end meeting,
- receive end package (summary, minutes, action items).
- all control/read endpoints protected by Supabase Auth JWT validation.

## Scope
In scope:
- Supabase Auth integration for API and web baseline.
- JWT validation middleware/guard on debate endpoints.
- tenant/workspace-scoped access checks for debate resources.
- realtime event streaming endpoint (SSE).
- control endpoints for pause/resume/intervene/end.
- debate runtime state machine (`pending`, `running`, `paused`, `ended`).
- intervention event persistence and response integration.
- end-of-meeting output generation path.
- minimal operator UI page in `apps/web` to observe and control flow.

Out of scope:
- voice mode.
- persona builder UI.
- advanced memory retrieval.

## Mandatory Standards
Follow:
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/08-realtime-discussion-and-intervention-protocol.md`
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/16-milestone-gates-and-evidence.md`
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/17-decisions-log.md`
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/03-dark-matte-design-system.md`
- OpenRouter-only provider policy.
- Supabase Auth as auth provider baseline (with future SSO extension path).

## Prerequisite
- Ticket-05.1 passed.

## Cursor Instructions
1. Work only in `arinar-v2/`.
2. Extend backend (`apps/api`) with endpoints:
- `POST /debates` (if needed for lifecycle)
- `POST /debates/{debate_id}/start`
- `POST /debates/{debate_id}/pause`
- `POST /debates/{debate_id}/resume`
- `POST /debates/{debate_id}/intervene`
- `POST /debates/{debate_id}/end`
- `GET /debates/{debate_id}/events/stream` (SSE)
3. Add auth baseline:
- validate Supabase JWT on protected endpoints.
- require authenticated user identity for start/pause/resume/intervene/end/stream.
- enforce workspace/tenant access check before debate actions.
4. Python hygiene:
- standardize local API test commands with project `.venv` path support.
- remove current pytest warnings in API tests (pydantic config/field namespace warnings).
3. Implement runtime rules:
- only running debates emit turn events.
- pause halts new turns.
- intervene creates `intervention` event and injects user message into flow.
- end stops further turns and emits final package.
5. Event model:
- reuse existing event schemas where possible.
- persist all control and agent events in `events` ledger.
6. Minimal web operator page in `apps/web`:
- dark matte styling aligned with design doc.
- live feed panel (SSE).
- controls: start, pause, resume, intervene, end.
- intervention input supporting `@agent` mention text.
7. Auth UI baseline:
- add basic sign-in/session plumbing using Supabase client in web app.
- pass auth token to API requests.
8. Contracts:
- update OpenAPI and generated types to include M2 endpoints/payloads.
9. Tests:
- backend state transition tests.
- pause/resume behavior test.
- intervention while running test.
- intervention after end must fail.
- end always returns/records summary package.
- unauthorized access to protected endpoints must fail.
- cross-workspace access attempt must fail.

## Deliverables
- working live stream + control endpoints.
- Supabase Auth integration baseline in API/web.
- minimal operator UI for M2 acceptance.
- contract and tests updated.
- runbook: `docs/runbooks/m2-realtime-controls.md`.

## Validation Checklist
- live feed updates during running debate.
- protected endpoints reject missing/invalid JWT.
- workspace-scope checks enforced.
- pause prevents new turn events.
- resume continues turn events.
- intervene accepted only in valid state.
- end transitions to terminal state and emits outputs.

## Test/Verify Commands
Run and include output summary:
- `make verify`
- API tests for state transitions/control paths
- API auth tests (invalid JWT, unauthorized workspace)
- one end-to-end local demo flow (start -> pause -> intervene -> resume -> end)

## Reporting (Mandatory)
1. create report file:
- `bash scripts/new_ticket_report.sh TICKET-06`
2. fill report with command evidence.
3. update index:
- `/Users/pv/Downloads/arinar-6-IPSS-V5/arinar-v2/reports/tickets/INDEX.md`
4. chat output only:
- report path
- final status
- blockers

## Definition of Done
- M2 gate passable from direct evidence:
- user can observe and control live debate and end cleanly with package outputs.
- auth baseline is active and unauthorized/cross-workspace requests are blocked.
