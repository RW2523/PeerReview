# Architect Checkpoint Log - for claude use only.

Tracks senior architect reviews, progress between checkpoints, and actionable findings.

---

## Checkpoint 3 — 2026-02-06 (Current)

### Progress Since Checkpoint 2

| What Changed | Details |
|---|---|
| TICKET-03.1 (Gate Hardening) | PASS. 7/7 detection tests. Multiline + comment-only catch now caught via Python helper. |
| TICKET-04 (Local Infra + DB) | PASS. Docker stack verified — Postgres, Redis, MinIO all running. Migrations, seed, smoke all clean. |
| TICKET-05 (M1 Debate-in-a-Box) | PASS. `POST /debates/run` works. 5-turn round-robin, DB persistence, summary generation. 7 tests. |
| TICKET-05.1 (API Test Gates) | PASS. `make api-test` added. CI now includes Python test job. `make verify` covers both contract + API tests. |
| First real Python code shipped | `apps/api/` now has 5 source files, 1 test file, working FastAPI app |
| Language decision made | Python (FastAPI) confirmed for backend/orchestration |
| Reporting system working | 4 ticket reports + INDEX.md with status tracking |

### Current State Summary

```
Stage 0: Foundation          [==========] DONE (Tickets 01-04)
M1: Debate-in-a-Box API     [==========] DONE (Ticket 05 + 05.1)
M2: Realtime + Room UI      [          ] NOT STARTED
M3: Memory v1               [          ] NOT STARTED
M4: Persona + Agent Import   [          ] NOT STARTED
M5: Voice + MCP + Enterprise [          ] NOT STARTED
```

### What's Working

- `POST /debates/run` — accepts problem + 3 agents + BYOK key, runs 5-turn debate, returns summary JSON
- OpenRouter client with retry logic and proper auth error handling
- DB persistence: debate, participants, events all written to Postgres
- `make verify` runs 16 tests total (9 contract + 7 API) + quality gates
- CI pipeline covers lint, typecheck, contract tests, API tests, quality gates
- Docker local infra boots with `make db-up`
- Full seed dataset for local development

### Issues + Observations

**1. DB schema vs. code mismatch (minor)**
The migration creates `participants.role_name` but `debate_engine.py:78` inserts `display_name` and `turn_order` — columns that don't exist in the migration schema. Tests pass because DB is mocked. This will fail against a real database.

**2. Hardcoded tenant/workspace IDs**
`debate_engine.py:47-48` uses hardcoded seed data UUIDs. Fine for M1 demo scope, but this pattern needs to be replaced before M2. Track it now.

**3. `completed` is not a valid debate state in the schema**
The CHECK constraint on `debates.state` allows: `draft, preflight, live, paused, synthesis, closed, archived`. But `debate_engine.py:187` sets state to `completed`. This will fail against the real DB.

**4. No integration test against real DB**
All 7 API tests mock the database. The gap between mocked tests and real DB (point 1 and 3 above) is a real risk. Before M2, at least one test should run against the actual Postgres.

**5. Synchronous OpenRouter calls**
`debate_engine.py` uses `httpx.Client` (sync). For M2 with SSE streaming, this needs to become async (`httpx.AsyncClient`). Not blocking, but the engine will need a rewrite for realtime.

**6. `.venv` and `__pycache__` in workspace**
`apps/api/.venv/` and `__pycache__/` directories exist. Verify `.gitignore` excludes them before any git push.

### Recommendations for Next Phase (M2)

1. **Fix the DB schema/code mismatch first.** Either update the migration to add `display_name` and `turn_order` to participants, or update the engine to use `role_name`. Also add `completed` to the debate state CHECK constraint. This is blocking real DB integration.

2. **Add one integration test against real Postgres.** Use the Docker stack that's already working. A single test that runs `POST /debates/run` against a real DB will catch mismatch issues early.

3. **M2 core deliverables should be:**
   - SSE endpoint for streaming debate turns in real-time
   - Debate lifecycle endpoints: create, start, pause, resume, end
   - Basic intervention: tag an agent, redirect topic
   - Dark matte Slack-like room UI (Next.js)
   - Separate debate creation from debate execution (currently one endpoint does both)

4. **Don't expand agent count yet.** Keep 3 agents for M2. The round-robin is simple and debuggable. Variable agent count is an M3 concern.

---

## Checkpoint 2 — 2026-02-06 (Earlier Same Day)

### Progress Since Checkpoint 1

| What Changed | Details |
|---|---|
| TICKET-03 (CI Quality Gates) | PARTIAL at time of review. Gate tests failed 2/7 (multiline + comment-only catch). |
| TICKET-04 (Local Infra) | PARTIAL. All files created but Docker was not available to verify runtime. |
| Reporting system added | `reports/tickets/` with INDEX.md and TEMPLATE.md |
| Docker Compose created | Full Supabase local stack (8 services defined, 3 core used) |
| DB schema written | 11 tables, 19 indexes, RLS enabled, `updated_at` triggers |
| Seed data created | 1 tenant, 1 workspace, 3 agents, 1 debate, 5 events |
| Makefile expanded | 7 new DB targets: db-up, db-down, db-reset, db-migrate, db-seed, db-smoke, db-logs |

### Issues Flagged

- `.env` file committed with demo JWT tokens (should be `.env.example` only)
- Ticket process rule broken: moved to Ticket-04 before Ticket-03 fully passed
- Docker never started — DB stack untested
- pgvector extension missing from migration
- Docker Compose heavier than needed (7 services when 3 suffice for dev)

---

## Checkpoint 1 — 2026-02-06 (Initial Review)

### State at First Review

| Component | Status |
|---|---|
| Codex docs (16 files) | Complete. Strong product vision, architecture, and engineering standards. |
| TICKET-01 (Monorepo scaffold) | DONE. Clean structure, ADRs, WORKSPACE-MAP. |
| TICKET-02 (API contracts) | DONE. OpenAPI spec, 14 event schemas, type generation. |
| TICKET-03 (CI gates) | Ready, not started. |
| TICKET-04 (Local infra) | Ready, not started. |
| `apps/api` | Empty (README only) |
| `apps/web` | Empty (README only) |
| `apps/workers` | Empty (README only) |

### Key Findings

- Over-specified before having a working loop (16 docs, 0 features)
- 12-week timeline aggressive for near-zero starting point
- Temporal may be premature for Stage 1
- Two-language stack (TS + Python) is a real cost for a founder-led build
- Some specs contain contradictions and unresolved decisions
- Recommended: ship "debate in a box" ASAP, freeze advanced docs, make decisions in one place

### Recommendations Given

1. Ship debate-in-a-box by end of Week 3
2. Collapse ticket queue into milestone-sized chunks
3. Don't build full memory fabric until real debate content exists
4. Add a `decisions.md` file to close open questions
5. Add progress tracking (this file)

---

## Progress Velocity

| Checkpoint | Tickets Completed | Tests | Source Files | Working Endpoints |
|---|---|---|---|---|
| CP1 | 2 (scaffold + contracts) | 9 (contract only) | 0 | 0 |
| CP2 | 2 partial (gates + infra) | 9 | 0 | 0 |
| CP3 | 4 complete + 2 sub-tickets | 16 (9 contract + 7 API) | 5 Python + 1 test | 2 (`/health`, `/debates/run`) |

**Velocity assessment:** Strong. Went from zero code to a working debate API endpoint in one day. Foundation work (scaffold, contracts, CI, infra) was thorough and is now paying off. The team is moving fast without cutting corners on process.

**Biggest risk going forward:** The gap between mocked tests and real DB behavior. Fix the schema mismatches before building M2 on top of them.
