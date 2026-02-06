# TICKET-04: Local Infra, DB Bootstrap, and Initial Migrations

## Status
- `ready`

## Objective
Bootstrap local infra and initial database/migration setup so feature tickets can build on stable foundations.

## Scope
In scope:
- Local infra orchestration (Postgres, Redis, object storage mock).
- Migration tool setup.
- Initial schema for core entities and memory fabric.
- Seed script for local demo data.

Out of scope:
- Full production hardening.
- Business feature completeness.

## Mandatory Standards
Follow:
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/06-memory-fabric-architecture-2026.md`
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/11-agent-continuity-and-knowledge-transfer.md`
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/15-engineering-standards-and-anti-chaos-rules.md`
- Model-provider policy: OpenRouter-only. No direct OpenAI provider integration.

## Prerequisite
- Ticket-03 completed.

## Cursor Instructions
1. Work inside `arinar-v2/`.
2. Add local infra config:
- `infra/docker/docker-compose.yml` with:
  - Postgres
  - Redis
  - MinIO (or equivalent S3-compatible local storage)
3. Add migration setup (choose one tool and document it):
- Alembic (recommended for FastAPI Python stack).
4. Create initial migrations for:
- `tenants` / `workspaces` (minimal tenant boundary)
- `debates`
- `participants`
- `events` (session event ledger)
- `memory_events`
- `memory_state`
- `memory_chunks`
- `agents`
- `agent_knowledge_units`
- `memory_access_log`
5. Ensure key indexes for:
- tenant/workspace scoping
- debate event retrieval
- vector search (if extension enabled)
6. Add seed script:
- one tenant/workspace
- one sample debate
- sample participants and minimal event history
7. Add runbook:
- `docs/runbooks/local-infra-and-migrations.md` with setup, reset, rollback, and troubleshooting.

## Founder Action Required (Blocking for Staging/Prod)
Please provide:
1. Target staging DB provider (`Supabase` or `Managed Postgres`).
2. Whether pgvector is available in target environment.
3. Staging connection details once ready (you can share later when moving beyond local).

If not yet decided, complete this ticket in local-only mode with configurable env placeholders.

## Deliverables
- Local infra boot command.
- Initial migration chain.
- Seed data script.
- Runbook for developers and AI coding agents.

## Validation Checklist
- Local services start cleanly.
- Migrations apply from empty DB.
- Seed script runs without manual SQL edits.
- Rollback or reset path documented.

## Test/Verify Commands
Run and include output summary:
- local infra up command.
- migration apply command.
- seed command.
- quick SQL sanity check for core tables.

## Definition of Done
- Local platform foundation exists for feature development.
- Core schemas align with architecture docs.
- Ready for next feature ticket series.
