# Engineering Standards and Anti-Chaos Rules (2026)

## Purpose
Prevent codebase drift while multiple AI coding agents build fast.

This file is mandatory for all implementation stages.

## 1) Monorepo Folder Structure (Required)
Use this shape and keep boundaries strict:

```text
arinar/
  apps/
    web/                  # Next.js app (UI + BFF endpoints only)
    api/                  # FastAPI app (domain APIs, orchestration endpoints)
    workers/              # background jobs (Temporal/workers/ingestion)
  packages/
    contracts/            # OpenAPI/JSON schemas/types shared across apps
    ui/                   # reusable UI components/tokens
    prompts/              # prompt templates + compilation utilities
    tooling/              # lint/test/dev scripts
  infra/
    migrations/           # SQL migrations
    docker/               # local infrastructure configs
  tests/
    e2e/                  # end-to-end tests
    integration/          # cross-service integration tests
  docs/
    architecture/
    runbooks/
```

Rules:
- no business logic in `apps/web` UI components,
- no direct DB writes from frontend,
- no cross-imports that bypass package boundaries.

## 2) File Naming Rules
- Use explicit names, no vague files like `utils2.ts`, `temp_fix.py`, `new.py`.
- API handlers: `<domain>_routes.py` or `<domain>.routes.ts`.
- Services: `<domain>_service.py` / `<domain>Service.ts`.
- Tests mirror source names: `x_service.py` -> `test_x_service.py`.
- Migration files: timestamp + short description.

## 3) File Size Limits (Hard)
- Max `300` lines for UI components.
- Max `400` lines for service files.
- Max `500` lines for route/controller files.
- If limit is exceeded, refactor before merge.

Exceptions:
- generated files (must be clearly marked/generated path).

## 4) Refactoring Discipline
When editing old code:
1. Preserve behavior first.
2. Add tests for current behavior.
3. Refactor in small commits/patches.
4. Re-run tests after each refactor.

Never:
- mix feature changes and large refactors in one patch,
- leave dead code paths untracked,
- add fallback hacks without TODO + issue link.

## 5) Duplicate Prevention Rules
Before creating new modules:
- search for existing similar functionality,
- extend existing module when domain matches.

Must-run checks before merge:
- duplicate files check,
- duplicate API route check,
- duplicate SQL/table definition check.

Guideline commands:
- `rg` search for existing symbols/endpoints before adding new ones.
- Use CI lint checks to fail on duplicated exported names where possible.

## 6) API Contract Rules
- API-first: define/update schema before implementation.
- Every endpoint must include:
  - purpose,
  - request schema,
  - response schema,
  - error codes.
- No untyped `any` payloads in public interfaces.
- Keep endpoint naming consistent and domain-scoped.

## 7) Commenting and Docstring Rules
Required comments:
- public APIs,
- non-obvious business rules,
- safety/policy enforcement blocks.

Avoid:
- trivial comments,
- stale comments after refactor.

Each public function/class should explain:
- what it does,
- key inputs/outputs,
- side effects.

## 8) Test Requirements (No Merge Without)
For every feature:
- unit tests for core logic,
- integration tests for API and DB behavior,
- e2e test for critical user flow when applicable.

Mandatory coverage focus:
- policy enforcement,
- tenant isolation,
- no-assumption response guardrails,
- knowledge import boundaries,
- citation provenance.

## 9) Definition of Done (Per Ticket)
A ticket is done only if:
1. feature works,
2. tests pass,
3. contracts updated,
4. docs updated,
5. no new duplication or oversized files,
6. rollback path documented if migrations changed.

## 10) PR/Review Checklist (Use Every Time)
- Scope matches ticket (no hidden extras).
- No boundary violations between apps/packages.
- No direct secret/service-key misuse.
- API schemas and generated types updated.
- Tests are deterministic (no flaky sleeps/timeouts).
- Naming/readability meets standards.

## 11) Anti-Patterns (Block Immediately)
- giant “god files”,
- silent fallback behavior,
- copy-pasted service logic,
- direct production-only hacks,
- undocumented env vars,
- inconsistent event names across systems.

## 12) AI Coding Agent Rules (Codex/Cursor)
Each implementation prompt should include:
- exact files allowed to change,
- acceptance criteria,
- tests required,
- file size constraints,
- explicit instruction to avoid duplicate modules.

Default instruction:
"Do not create new files if an existing module should be extended."

## 13) Enforcement
Add CI checks for:
- lint + format,
- type checks,
- unit/integration tests,
- contract drift,
- max-file-length policy,
- forbidden-pattern scans (service-key misuse, temporary hacks).
