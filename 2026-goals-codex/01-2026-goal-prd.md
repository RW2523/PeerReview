# Arinar 2026 Goal PRD

## Product Thesis
Arinar becomes the enterprise system for **AI-facilitated decision rooms**: structured, evidence-backed debates between role-based AI participants, with a clear decision output that teams can trust.

## Core 2026 Goal
Launch a production-grade V1 where enterprise teams can:
1. Create a debate room from a business objective.
2. Assign AI roles and debate rules.
3. Upload context documents.
4. Run a live debate with citations.
5. Get a decision memo, risks, and action items.

All model calls must run through **user-provided OpenRouter API keys (BYOK)**.

## ICP and Target Users
- Mid-market and enterprise product/strategy teams.
- PMO/strategy offices, transformation teams, and innovation groups.
- Agencies running structured workshops for clients.

## V1 Scope (Launch Scope)
- Multi-role text debate rooms (3-8 active participants, up to 12 including review-only roles).
- Role + persona templates (exec, product, engineering, finance, legal, domain experts).
- Persona creation modes: preset template, AI-generated draft from minimal user input, custom manual.
- Per-participant prompt preview and pre-launch fine-tuning.
- Participant mode selection: new agent, import existing agent, or clone persona-only.
- Cross-meeting agent continuity with scoped knowledge import.
- Per-participant model mapping via OpenRouter.
- Document upload + indexing + citations.
- Human intervention controls (pause, redirect, ask role, end now).
- Timeboxed meeting controls with host warnings and end-mode policy.
- Final outputs: executive summary, minutes of meeting, action items, dissent notes, risks, evidence map.
- Audit trail of prompts, responses, and citations per debate.
- OpenRouter BYOK key management.
- Policy-controlled internet research for selected agents (off by default).
- Strict no-assumptions answer policy with explicit unknown/inference handling.

## Explicitly Out of Scope (V1)
- Voice mode.
- Autonomous long-horizon agents.
- Cross-room autonomous memory without explicit user controls.
- Advanced scoring systems as hard dependencies for launch.

## Enterprise Requirements
- Multi-tenant org/workspace boundary.
- SSO (SAML/OIDC), RBAC, and audit logs.
- Data residency-ready architecture.
- Encryption at rest and in transit.
- Configurable retention/deletion policy.
- External research policy controls (allowlists, approval mode, budget limits).

## Success Metrics (first 90 days post-launch)
- Time-to-first-decision: < 20 minutes median.
- Debate completion rate: > 70%.
- Citation coverage: > 80% of final decision claims linked to evidence.
- Minutes/action-item generation success: > 95% of ended debates.
- Weekly active organizations: target defined by GTM plan.
- P95 debate turn latency: < 8 seconds (non-document-heavy turns).

## Product Principles
- Structured over open-ended.
- Evidence over opinion.
- Reliable over clever.
- Enterprise trust over demo wow.

## North-Star User Story
"As a strategy lead, I can run a high-quality AI boardroom debate from my docs and get a clear, defensible decision memo in one session."
