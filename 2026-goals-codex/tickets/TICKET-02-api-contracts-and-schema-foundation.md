# TICKET-02: API Contracts and Schema Foundation

## Status
- `ready`

## Objective
Create canonical contracts first (OpenAPI + event schemas + generated types) before any API feature coding.

Terminology note:
- `OpenAPI` here means HTTP API specification format, not OpenAI provider usage.

## Scope
In scope:
- OpenAPI baseline for core debate lifecycle.
- Event schema definitions aligned with realtime protocol.
- Type generation pipeline for frontend/backend.

Out of scope:
- Full endpoint business logic.
- DB persistence.

## Mandatory Standards
Follow:
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/15-engineering-standards-and-anti-chaos-rules.md`
- `/Users/pv/Downloads/arinar-6-IPSS-V5/2026-goals-codex/08-realtime-discussion-and-intervention-protocol.md`
- Model-provider policy: OpenRouter-only. Do not add direct OpenAI provider integration.

## Prerequisite
- Ticket-01 completed.

## Cursor Instructions
1. Work inside `arinar-v2/`.
2. Create contracts layout:
- `arinar-v2/packages/contracts/openapi/arinar-v1.yaml`
- `arinar-v2/packages/contracts/schemas/events/*.schema.json`
- `arinar-v2/packages/contracts/src/generated/` (generated, git-tracked if desired)
3. Define minimal endpoints in OpenAPI:
- `GET /health`
- `POST /debates`
- `POST /debates/{debate_id}/participants`
- `POST /debates/{debate_id}/start`
- `POST /debates/{debate_id}/intervene`
- `POST /debates/{debate_id}/end`
- `GET /debates/{debate_id}/events`
4. Add event enums including:
- `agent_message`, `intervention`, `pre_turn_nudge`
- `research_request`, `research_result`, `research_denied`
- `tool_call_request`, `tool_call_result`, `tool_call_denied`
- `knowledge_imported`, `knowledge_rejected`, `unknown_response`
- `voice_transcript_partial`, `voice_transcript_final`
5. Add generation scripts:
- `generate:types` for TS types from OpenAPI.
- optional schema validation script for sample payloads.
6. Add lightweight contract tests to ensure schemas compile/validate.

## Founder Action Required (Blocking if missing)
Provide decisions before finalizing contracts:
1. Debate ID format: UUID v4 (`yes/no`).
2. Timestamps: UTC ISO-8601 (`yes/no`).
3. Default pagination style for events (`cursor` recommended).

If no answer is received, use defaults:
- UUID v4, UTC ISO-8601, cursor pagination.

## Deliverables
- Canonical OpenAPI baseline.
- Event schemas and generated types.
- Contract generation/validation scripts.

## Validation Checklist
- OpenAPI parses without errors.
- Types generation succeeds.
- Event schema includes all required event types from product docs.

## Test/Verify Commands
Run and include output summary:
- OpenAPI lint/validate command used in repo.
- Type generation command.
- Schema validation test command.

## Definition of Done
- Contracts are source of truth.
- Generated types are in sync.
- Ready for Ticket-03.
