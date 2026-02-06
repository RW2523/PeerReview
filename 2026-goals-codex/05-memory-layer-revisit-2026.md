# 2026 Memory Layer Revisit (Product + Architecture)

## Why this doc exists
You were right to revisit memory. In this repo, memory is not an optional enhancement. It is part of the product moat:
- debate continuity across turns and sessions,
- document-grounded responses with citations,
- persona consistency over time,
- enterprise auditability of reasoning.

## Quick verdict on your friend's 2026 draft
What is strong and should be kept:
- Keep memory as a first-class differentiator, not a utility.
- Keep `OpenRouter BYOK` as model access and keep memory decoupled from model provider.
- Keep a simpler topology (fewer moving parts than 2025).
- Keep pgvector as the baseline retrieval engine.

What is directionally right but needs correction:
- "Single-store only" is too absolute. You still need separate runtime state vs persistent memory concerns.
- A pure Next.js-only backend will constrain long-running ingestion/retrieval workers and memory pipelines.
- "SSE replaces all realtime complexity" is true for token streaming, but not for collaborative room events at enterprise scale.
- Cross-session memory needs explicit governance (retention, deletion, tenant isolation), not only embeddings.

## What the 2025 memory code tells us
### Current active implementation is a fallback stub
- `fastapi/app/services/memory_manager.py:1` explicitly says it is a minimal server-unblock version.
- Only a tiny subset is implemented (`store_memory`, limited adapter behavior).

### Core runtime expects richer memory contracts that are missing today
- Orchestrator calls methods absent from active manager:
  - `store_long_term_memory` at `fastapi/app/services/debate_orchestrator.py:78`
  - `store_episodic_memory` at `fastapi/app/services/debate_orchestrator.py:107`
- Debate API calls absent method:
  - `store_debate_metadata` at `fastapi/app/api/debate.py:229`
- Discussion Host expects absent adapter APIs:
  - `initialize` at `fastapi/app/services/discussion_host/host_controller.py:140`
  - `store_discussion_state` at `fastapi/app/services/discussion_host/host_controller.py:227`
  - `store_message` at `fastapi/app/services/discussion_host/host_controller.py:301`
- Document context expects absent document APIs:
  - `get_document_memories` at `fastapi/app/services/discussion_host/document_context_manager.py:58`
  - `get_document_context_for_prompt` at `fastapi/app/services/discussion_host/document_context_manager.py:270`

### Legacy memory logic has valuable ideas but source files are corrupted
- Backup files contain important domain methods and flows (`memory_manager.py.bak`, `.broken`, `.old`, `.bak2`).
- They do not parse cleanly:
  - `fastapi/app/services/memory_manager.py.bak` fails with unterminated triple quote near line 2158.
  - Same class of syntax failure in `.broken`, `.old`, `.bak2`.
- Example corruption is visible where function body is cut by docstring text:
  - `fastapi/app/services/memory_manager.py.broken:1208`

### Legacy design elements worth salvaging (concept, not file-copy)
- Domain APIs:
  - discussion state methods,
  - message history methods,
  - persona memory methods,
  - document knowledge/context methods.
- Memory taxonomy:
  - short-term, long-term, episodic, semantic,
  - plus discussion/persona/document domains.
- Retrieval intent:
  - blended immediate context + persistent context model.

## 2026 memory architecture (recommended)
### Product requirements for memory
- `P1`: Debate continuity within room (fast retrieval each turn).
- `P1`: Cross-session recall per workspace and persona.
- `P1`: Cross-meeting agent continuity with importable known knowledge.
- `P1`: Document-grounded answer support with citation provenance.
- `P1`: Full tenant isolation and auditable access history.
- `P2`: Memory quality scoring and consolidation jobs.

### Service shape (simple but scalable)
1. `Memory API` (Python/FastAPI): canonical contracts for write/read/search.
2. `Memory Worker` (Python): ingestion, chunking, summarization, consolidation, re-embedding.
3. `Postgres + pgvector`: persistent memory store and vector search.
4. `Redis`: short-lived turn cache and hot-context acceleration.

This keeps architecture small while preserving enterprise-scale behavior.

### Why Python still matters here
- Your existing orchestration and memory logic is Python-heavy; rewrite risk is high.
- Memory pipelines are async/background heavy and benefit from Python ecosystem maturity for ETL/NLP and workflow workers.
- Keeping Next.js focused on product UI/BFF avoids overloading Server Actions with long-running memory tasks.
- Result: JS for product velocity, Python for memory/orchestration reliability.

## Canonical memory model for V1
Use one core table plus optional denormalized views/materialized projections.

### `memories` (single canonical write table)
- `id` (UUID)
- `tenant_id` (UUID)
- `workspace_id` (UUID)
- `debate_id` (UUID nullable)
- `scope` (`runtime|debate|workspace|persona|document`)
- `memory_type` (`short_term|episodic|semantic|summary|decision`)
- `content` (text/jsonb)
- `embedding` (vector)
- `metadata` (jsonb; citation, speaker, timestamps, tags)
- `source_ref` (doc/message/event id)
- `created_at`, `expires_at`, `version`, `deleted_at`

### Retrieval strategy per turn
1. Fetch last `N` runtime events (cheap, deterministic).
2. Semantic search on scoped memories (debate + workspace + persona).
3. Merge document evidence context with citation anchors.
4. Rerank + budget by token window.
5. Return an explainable context bundle (for audit/export).

### Guardrails
- Strict tenant filters before vector search.
- No direct service-role inserts in request path.
- Retention policies by scope/type (automatic expiry for short-term).
- Soft delete + hard delete job for compliance workflows.
- Access log for all memory reads/writes tied to actor and request id.

## What to carry from your friend's work into ours
Take as-is:
- BYOK OpenRouter direction.
- Simplified service count.
- Dark matte UI continuity.
- pgvector-first memory base.

Take with modification:
- Keep LangGraph/Temporal style workflow orchestration only if needed for deterministic retries; do not let framework choice block V1.
- Keep SSE for model token streaming, but preserve pub/sub for room state fan-out where needed.
- Keep "IPSS 2.0 simplification", but preserve explicit citation and provenance outputs.

Do not carry forward:
- Assumptions that modern context windows remove need for structured memory.
- Memory implemented as framework side-effect rather than explicit product subsystem.
- Any direct copy of corrupted 2025 memory files.

## Migration plan from 2025 -> 2026 memory
1. Define a strict `IMemoryService` interface and freeze contracts.
2. Implement contract-complete adapter that matches expected methods currently called by orchestrator/host.
3. Add canonical `memories` schema + migrations.
4. Re-implement only high-value flows first:
   - `store_discussion_state/get_discussion_state`
   - `store_message/get_recent_messages`
   - `store_document_knowledge/get_document_context_for_prompt`
5. Add regression tests mapped to current call sites.
6. Remove fallback stub and delete dead backup variants after parity tests pass.

## Bottom line
Memory is still core to this product in 2026. The right move is not "keep old code" or "drop memory complexity entirely." The right move is:
- preserve the 2025 memory product intent,
- rebuild memory contracts and persistence cleanly,
- keep Python for memory/orchestration services,
- let Next.js own product UI and user workflows.
