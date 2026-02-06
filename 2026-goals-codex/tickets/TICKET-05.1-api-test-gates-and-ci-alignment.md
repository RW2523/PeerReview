# TICKET-05.1: API Test Gates and CI Alignment (Close M1 Verification Gap)

## Status
- `ready`

## Objective
Ensure M1 is actually protected by automation:
- `apps/api` tests must run in local verify flow and CI.
- no pass status if only contracts/tests run while API tests are skipped.

## Why This Ticket Exists
Current `make verify` validates contracts and quality scripts, but does not enforce API test execution.  
This creates a regression risk for `POST /debates/run`.

## Scope
In scope:
- add deterministic API test command wiring.
- include API tests in `make verify`.
- include API tests in CI workflow.
- update runbook for Python env setup.

Out of scope:
- new feature behavior.
- endpoint contract changes.

## Mandatory Standards
Follow:
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/15-engineering-standards-and-anti-chaos-rules.md`
- `/Users/pv/Downloads/arinar-6-IPSS-V5/arinar-v2/WORKSPACE-MAP.md`
- OpenRouter-only provider policy.

## Cursor Instructions
1. Work only in `arinar-v2/`.
2. Add Makefile targets for API tests, example:
- `make api-test`
- `make verify` must call `api-test` (or equivalent) and fail if tests fail.
3. Ensure reproducible Python test environment for `apps/api`:
- choose simple approach (venv + `requirements-dev.txt`).
- avoid hidden global dependency assumptions.
4. Update CI (`.github/workflows/ci.yml`) to run `apps/api` tests in addition to existing checks.
5. Update docs:
- `docs/runbooks/ci-gates.md` and/or API runbook with exact local test setup commands.

## Deliverables
- API tests are mandatory in local verify and CI.
- documented setup for running API tests from clean machine.

## Validation Checklist
- `make verify` fails if `apps/api` tests fail.
- CI fails if `apps/api` tests fail.
- fresh environment can run API tests using documented commands.

## Test/Verify Commands
Run and include output summary:
- `make api-test`
- `make verify`
- local CI-equivalent run (or job command list)

## Reporting (Mandatory)
1. create report file:
- `bash scripts/new_ticket_report.sh TICKET-05.1`
2. fill report with command evidence.
3. update index:
- `/Users/pv/Downloads/arinar-6-IPSS-V5/arinar-v2/reports/tickets/INDEX.md`
4. chat output only:
- report path
- final status
- blockers

## Definition of Done
- M1 core API is protected by hard test gates locally and in CI.
- Ready for Ticket-06 (M2 realtime/control).

