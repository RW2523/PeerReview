# 2026 Memory Fabric Architecture (Better Than 4-Layer)

## Context from the X post
Reference: [pbteja1998 post](https://x.com/pbteja1998/status/2017495026230775832?s=61)

What is useful for Arinar:
- Mission-control operating model (many agents, shared queue, live feed).
- Agents collaborate, refute, review, and self-assign tasks.
- System is event-heavy, not just prompt/response chat.

For your product, this means memory must support:
- shared state across many role agents,
- verifiable history of who said what and why,
- real-time handoff between agents and user,
- enterprise audit and policy enforcement.

## Why the old 4-layer model is not enough by itself
The old `short/long/episodic/semantic` split is good conceptually, but weak operationally:
- it does not define deterministic state reconstruction,
- it does not define multi-agent coordination memory,
- it does not define citation provenance as first-class,
- it does not define governance and deletion at enterprise scale.

## Recommended replacement: Memory Fabric (6 components)
This keeps the spirit of 4-layer memory, but adds reliability and enterprise controls.

1. `Event Ledger` (source of truth)
- Immutable append-only records for every debate event.
- Examples: turn_started, message_posted, evidence_attached, challenge_raised, decision_locked.
- Rebuild any debate timeline exactly.

2. `Operational State Store`
- Materialized current state for fast app reads.
- Examples: current speaker, active tasks, unresolved objections, turn budget.
- Built from Event Ledger projections.

3. `Semantic Retrieval Store` (pgvector)
- Embeddings for messages, summaries, document chunks, decisions.
- Embeddings for approved external research snippets with source metadata.
- Scoped retrieval by `tenant/workspace/debate/persona`.
- Powers context injection for each model turn.

4. `Evidence Graph`
- Directed links between claims, sources, rebuttals, and outcomes.
- Enables “show me evidence for this conclusion” and dissent tracking.
- Core for enterprise trust and exportable decision memos.

5. `Persona/Agent Profile Memory`
- Stable behavioral and preference memory per role/persona.
- Includes style constraints, role goals, and learned preferences.
- Prevents role drift over long debates.
- Supports persistent agent identity across meetings.

6. `Governance Memory`
- Retention, legal hold, deletion workflows, access logs, policy violations.
- Required for enterprise procurement and compliance reviews.

## Minimal stack to ship this
- `Next.js` for product UI + BFF.
- `Python/FastAPI` for memory API and orchestration workers.
- `Postgres + pgvector` for ledger + projections + vector retrieval.
- `Redis` for hot working-set cache and fan-out buffers.
- `OpenRouter BYOK` only for model calls.

## Canonical data model
### `memory_events` (immutable)
- `id`, `tenant_id`, `workspace_id`, `debate_id`, `event_type`, `actor_type`, `actor_id`, `payload`, `created_at`, `trace_id`

### `memory_state` (projection)
- `debate_id`, `current_turn`, `active_agent`, `open_objections`, `latest_summary`, `updated_at`

### `memory_chunks` (semantic index)
- `id`, `scope`, `scope_id`, `chunk_type`, `content`, `embedding`, `metadata`, `source_url`, `created_at`, `expires_at`

### `agent_knowledge_units` (cross-meeting)
- `id`, `tenant_id`, `workspace_id`, `agent_id`, `statement`, `knowledge_type`, `source_event_ids`, `source_document_ids`, `confidence`, `created_at`, `expires_at`

### `evidence_edges`
- `id`, `debate_id`, `from_node`, `to_node`, `edge_type`, `confidence`, `metadata`, `created_at`

### `memory_access_log`
- `id`, `tenant_id`, `actor_id`, `operation`, `filters`, `result_count`, `created_at`

## Retrieval pipeline per agent turn
1. Read `memory_state` for deterministic current context.
2. Pull last `N` relevant events from `memory_events`.
3. Run scoped semantic search in `memory_chunks`.
4. Pull supporting edges from `evidence_edges`.
5. Compose a bounded `Context Packet` for the model.
6. Store model output back as event + chunk + evidence links.

## New memory contract (interface)
Required methods:
- `append_event(...)`
- `get_state(debate_id)`
- `search_semantic(query, scope, filters, limit)`
- `link_evidence(claim_id, source_id, relation, confidence)`
- `get_context_packet(debate_id, persona_id, query, token_budget)`
- `apply_retention_policy(scope, policy_id)`
- `import_agent_knowledge(agent_id, filters, mode)`
- `get_agent_known_facts(agent_id, confidence_threshold)`

## Enterprise controls
- Hard tenant filter in every query path.
- Envelope encryption for sensitive memory payloads.
- Soft delete + delayed hard delete jobs.
- Policy gates before model call (data class, allowed model, budget).
- Policy gates before external research indexing (allowed domain + approval).
- No-assumption output gates: publish only source-backed known claims by default.
- Full audit trail for memory read/write operations.

## Migration from your current code
1. Keep current API surface names where possible for compatibility.
2. Re-implement methods behind new fabric:
- `store_discussion_state`, `store_message`, `get_recent_messages`,
- `get_document_context_for_prompt`, `store_debate_metadata`.
3. Replace direct service-key insert patterns.
4. Add replay tests: given events, projected state must match expected debate state.
5. Phase out corrupted legacy files after parity.

## Why this is fundamentally better for Arinar
- Supports mission-control multi-agent behavior, not just chat memory.
- Gives deterministic replay and enterprise auditability.
- Improves retrieval quality through evidence-linked context packets.
- Scales operationally without losing explainability.
