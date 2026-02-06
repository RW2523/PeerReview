# Build Order Playbook (No-Code Founder Mode)

## Goal
Ship Arinar V1 without you writing code, using Codex/Cursor as implementation agents under strict scope and quality gates.

Mandatory companion standards:
- `15-engineering-standards-and-anti-chaos-rules.md`

## 1) Operating Model
You own:
- product decisions,
- priority and acceptance,
- policy approvals (security/compliance),
- design direction.

Codex/Cursor own:
- implementation,
- tests,
- migrations,
- bug fixes,
- docs updates.

Rule:
- no new feature starts until current gate passes.

## 2) Execution Sequence (Do Not Reorder)
### Stage 0: Project Reset and Guardrails (Week 1)
Deliver:
- clean monorepo structure,
- env templates,
- CI baseline,
- OpenAPI contract scaffold,
- seed data and local dev scripts.

Gate:
- app boots locally,
- CI runs lint + unit tests,
- typed API SDK generation works.

### Stage 1: Core Text Debate Loop (Weeks 2-3)
Deliver:
- create debate from problem statement,
- add participants (role + model mapping),
- start/pause/end debate,
- realtime text feed (SSE + pub/sub),
- basic summary output.

Gate:
- one end-to-end debate works with 3 agents,
- no critical errors in normal flow,
- replay of session events works.

### Stage 2: Persona System and Prompt Control (Week 4)
Deliver:
- persona source modes (preset/AI-generated/manual),
- prompt preview + edit before start,
- prompt validation and versioning.

Gate:
- each participant has validated prompt snapshot,
- invalid prompts block session start,
- audit shows prompt version used.

### Stage 3: Memory Fabric and Agent Continuity (Weeks 5-6)
Deliver:
- event ledger + state projection,
- semantic retrieval + evidence links,
- agent continuity modes (`new/import/clone`),
- strict no-assumption guardrail with `unknown_response`.

Gate:
- imported agent answers only from source-backed known knowledge,
- provenance visible for claims,
- cross-meeting knowledge leakage tests pass.

### Stage 4: Documents, Citations, End Package (Week 7)
Deliver:
- file upload and processing pipeline,
- citation rendering in debate feed,
- end package: executive summary, minutes, action items, dissent/risk.

Gate:
- citation coverage threshold met in staging tests,
- end package generated for >95% completed sessions.

### Stage 5: Internet Research Gateway (Week 8)
Deliver:
- policy-controlled research gateway (default off),
- per-agent permissions + allowlist + budgets,
- research event logging and source linking.

Gate:
- blocked policy paths proven,
- approved research returns citable sources,
- full audit logs captured.

### Stage 6: Tool Gateway + MCP Foundation (Week 9)
Deliver:
- tool registry,
- risk tiers T0-T3,
- approval workflows,
- MCP adapter behind feature flag.

Gate:
- unregistered tools blocked,
- approved tools run with audit trail,
- MCP calls restricted to allowlisted servers.

### Stage 7: Enterprise Hardening (Weeks 10-11)
Deliver:
- RBAC + SSO,
- retention/deletion controls,
- observability dashboards,
- reliability and load checks.

Gate:
- tenant isolation tests pass,
- error budget and latency targets met in staging.

### Stage 8: Beta Release (Week 12)
Deliver:
- pilot onboarding,
- runbooks,
- release checklist,
- rollback plan.

Gate:
- design-partner pilots complete,
- top P0/P1 issues resolved,
- release sign-off.

## 3) Founder Workflow (No Code)
For each stage:
1. Approve scope (1 page summary).
2. Ask Codex/Cursor to implement exact ticket set.
3. Review demo video/screens + acceptance checklist.
4. Approve or reject gate.
5. Move to next stage only after pass.

## 4) Ticket Format (Use This Every Time)
For each ticket require:
- objective,
- files expected to change,
- API/data contract impact,
- tests to add,
- acceptance criteria,
- rollback note.
- explicit file-size and no-duplicate compliance check.

## 5) Prompt Templates for Codex/Cursor
### Build Prompt
"Implement Stage X Ticket Y exactly as specified in `/2026-goals-codex`. Follow `15-engineering-standards-and-anti-chaos-rules.md` strictly. Do not expand scope. Add tests and update docs. Provide changed files and gate checklist."

### Fix Prompt
"Given failed gate criteria A/B/C, patch only required areas, keep contracts stable, and add regression tests."

### Review Prompt
"Run code review for regressions and security risks first. List findings by severity with file references."

## 6) Weekly Cadence
- Mon: finalize stage scope.
- Tue-Thu: implementation iterations.
- Fri: gate review and decision.

## 7) Non-Negotiable Quality Gates
- typed contracts enforced,
- no direct service-key bypass patterns,
- audit logs for sensitive operations,
- tenant boundary tests in CI,
- rollback plan for migrations.

## 8) What You Should Decide Early
- default enterprise policies (internet/tool access),
- participant cap for GA,
- persona compliance rules for style-based templates,
- export formats and retention policy defaults.

## 9) Voice and MCP Timing
- Voice/hybrid and deep MCP usage are post-core.
- Do not block V1 text product for voice.
- Keep interfaces ready now, but feature-flag advanced capabilities.

## 10) Success Definition for You
You are successful if:
- teams can run debates end-to-end,
- outputs are trusted and cited,
- imported agents reuse known context safely,
- you can operate the product without custom coding.
