# 2026 Execution Roadmap (Restart)

## Timeline
12 weeks to enterprise-ready V1 beta.

## Phase 0 (Week 1): Reset and Foundations
- Freeze old branch as reference only.
- Create new monorepo and service boundaries.
- Define canonical API schema (OpenAPI + typed frontend SDK generation).
- Implement org/workspace auth and RBAC skeleton.
- Finalize policy matrix (internet access, persona template governance, approval workflows).

## Phase 1 (Weeks 2-4): Core Product Loop
- Debate room creation and participant role assignment.
- Persona selection flow (preset, AI-generated, custom).
- Per-agent prompt preview and pre-launch fine-tuning.
- Agent continuity flow (new/import/clone persona-only).
- OpenRouter BYOK settings, validation, encrypted storage.
- Basic turn orchestration with Temporal workflow.
- Live debate view with reliable realtime updates (SSE + pub/sub).

## Phase 2 (Weeks 5-7): Document and Evidence Layer
- Upload pipeline to object storage.
- Chunking/embedding + retrieval in pgvector.
- Citation rendering linked to evidence snippets.
- Decision output generator (executive summary, minutes, actions, dissent, risks).
- Timebox and meeting-end workflow with host warning checkpoints.
- Agent knowledge unit extraction and cross-meeting import pipeline.

## Phase 3 (Weeks 8-10): Enterprise Hardening
- SSO integration (SAML/OIDC), audit logging.
- Tenant isolation tests and policy enforcement.
- Rate limiting, spend controls, and org-level model policies.
- Research gateway with domain allowlists and approval controls.
- Tool gateway and MCP adapter scaffolding behind feature flags.
- Observability dashboards (latency, errors, token costs).

## Phase 4 (Weeks 11-12): Beta Launch
- Pilot with design partners.
- Fix top reliability and UX issues.
- Final security checklist and runbooks.
- Release candidate and staged rollout.
- Voice/hybrid architecture spike complete with transcript normalization plan.

## Delivery Gates
- Gate 1: End-to-end debate works with one OpenRouter model.
- Gate 2: Evidence citations visible and exportable.
- Gate 3: Multi-tenant controls verified in automated tests.
- Gate 4: P95 latency and error-budget targets met in staging.
- Gate 5: Auto-generated minutes and action items validated for ended debates.
- Gate 6: Imported agents answer only from source-backed known knowledge in evaluation tests.

## Team Shape
- 1 Product lead.
- 1 Design lead.
- 2 Full-stack engineers.
- 1 Backend/platform engineer.
- 1 ML/orchestration engineer.
- 1 QA/automation engineer.

## Launch Risks and Mitigations
- Risk: model latency variability.
  - Mitigation: provider/model policy fallback through OpenRouter.
- Risk: orchestration regressions.
  - Mitigation: workflow determinism tests + replay tests.
- Risk: citation trust quality.
  - Mitigation: strict citation schema and evaluator checks.
