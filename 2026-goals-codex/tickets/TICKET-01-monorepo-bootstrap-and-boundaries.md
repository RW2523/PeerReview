# TICKET-01: Monorepo Bootstrap and Boundaries

## Status
- `ready`

## Objective
Bootstrap a clean V2 workspace with strict folder boundaries, while preserving the current legacy repo as reference.

## Scope
In scope:
- Create V2 root (`arinar-v2/`) if repo is not empty.
- Create required folder structure from standards doc.
- Add baseline root manifests and README files.
- Add architecture decision log placeholders.

Out of scope:
- Feature implementation.
- DB migrations.
- API route logic.

## Mandatory Standards
Follow:
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/15-engineering-standards-and-anti-chaos-rules.md`
- Model-provider policy: OpenRouter-only for this project. No direct OpenAI provider integration.

## Cursor Instructions
1. Preflight:
- If current root already contains legacy app code, create a new folder `arinar-v2/` and do all work inside it.
- Do not modify legacy app folders except adding documentation links if needed.
2. Create structure:
- `arinar-v2/apps/web`
- `arinar-v2/apps/api`
- `arinar-v2/apps/workers`
- `arinar-v2/packages/contracts`
- `arinar-v2/packages/ui`
- `arinar-v2/packages/prompts`
- `arinar-v2/packages/tooling`
- `arinar-v2/infra/migrations`
- `arinar-v2/infra/docker`
- `arinar-v2/tests/e2e`
- `arinar-v2/tests/integration`
- `arinar-v2/docs/architecture`
- `arinar-v2/docs/runbooks`
3. Add foundational files:
- `arinar-v2/README.md`
- `arinar-v2/docs/architecture/ADR-0001-repo-boundaries.md`
- `arinar-v2/docs/architecture/ADR-0002-service-boundaries.md`
- `arinar-v2/.editorconfig`
- `arinar-v2/.gitattributes`
- `arinar-v2/.gitignore`
4. Add short `README.md` in each top-level app/package folder with ownership and purpose.
5. Add a `WORKSPACE-MAP.md` describing allowed imports and forbidden cross-boundary patterns.

## Founder Action Required
- None for this ticket.

## Deliverables
- New `arinar-v2/` workspace scaffold with documented boundaries.

## Validation Checklist
- `tree arinar-v2 -L 2` shows all required folders.
- Every `apps/*` and `packages/*` folder has a clear README.
- No changes to legacy runtime code paths.

## Test/Verify Commands
Run and include output summary:
- `find arinar-v2 -maxdepth 2 -type d | sort`
- `rg -n "TODO|TBD" arinar-v2/docs/architecture`

## Definition of Done
- Structure created.
- Boundaries documented.
- No duplicate ambiguous folders.
- Ready for Ticket-02.
