# TICKET-03: CI Quality Gates and Anti-Dup Checks

## Status
- `ready`

## Objective
Set automated guardrails so fast coding does not degrade structure, quality, or safety.

## Scope
In scope:
- CI workflows for lint/type/test.
- File-size and duplicate checks.
- Contract drift checks.
- Required test command matrix docs.

Out of scope:
- Feature endpoint implementation.
- Performance/load testing.

## Mandatory Standards
Follow:
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/15-engineering-standards-and-anti-chaos-rules.md`
- Model-provider policy: OpenRouter-only. CI checks should not allow direct OpenAI provider dependencies.

## Prerequisite
- Ticket-02 completed.

## Cursor Instructions
1. Work inside `arinar-v2/`.
2. Create CI workflow(s) (GitHub Actions) for:
- lint checks (web/api/workers/contracts)
- type checks
- unit/integration tests
- contract generation consistency check
3. Add custom enforcement scripts:
- `check_file_sizes` (enforce max line counts from standards doc)
- `check_duplicates` (basic duplicate endpoint/file/symbol checks)
- `check_forbidden_patterns` (service-key misuse, temp fixes, known anti-pattern tokens)
  - include scan for direct provider SDK usage not routed through OpenRouter gateway.
4. Add a root `Makefile` or task runner commands for:
- `make lint`
- `make typecheck`
- `make test`
- `make verify`
5. Add `docs/runbooks/ci-gates.md` with explanations for each gate and common failure fixes.

## Founder Action Required
- None required to implement locally.
- For cloud CI execution, ensure repository actions are enabled.

## Deliverables
- Working CI pipeline with mandatory gates.
- Local equivalent commands matching CI.
- Runbook for debugging failed checks.

## Validation Checklist
- CI config exists and references all major workspaces.
- `verify` command runs all critical checks locally.
- Oversized-file and forbidden-pattern checks fail intentionally when violated.

## Test/Verify Commands
Run and include output summary:
- local `verify` command
- one intentional negative test (for example, simulated oversized file) proving gate failure.

## Definition of Done
- Quality gates are enforced automatically.
- No merge path exists without tests and contract checks.
- Ready for Ticket-04.
