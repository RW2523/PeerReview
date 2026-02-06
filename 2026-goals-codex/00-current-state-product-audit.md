# 2026 Restart: Current-State Product Audit

## 1) What this product is trying to be
Arinar is a **multi-AI enterprise decision room** where users:
- define a business problem,
- assign AI roles (CEO, CTO, CFO, Legal, etc.),
- upload context documents,
- run a structured debate,
- export decisions, action items, and evidence.

This core goal is still strong in 2026.

## 2) Why the original effort stalled (product view)
The repo shows strong ambition but low execution focus:
- Too many concurrent systems (IPSS, memory layers, debate host, personas, voice mode, OpenMemory, etc.) before stabilizing one reliable end-to-end flow.
- User value and platform depth were built in parallel, so neither reached production quality.
- Architecture drift between docs and implementation created high uncertainty.

## 3) Codebase reality summary
### Strong assets to keep
- Good conceptual product docs and role-based debate framing.
- A distinctive dark dashboard visual language worth preserving.
- Existing entities (debates, participants, personas, documents) map well to the 2026 product.

### Critical product risks in current code
1. Debate creation and orchestration path is internally inconsistent.
- `fastapi/app/api/debate.py:221` calls `orchestrator.initialize(..., speaking_order=...)`, but `fastapi/app/services/debate_orchestrator.py:49` has no `speaking_order` argument.
- `fastapi/app/services/debate_orchestrator.py:140` references `self.initialized` and `initialize_debate()` that are not defined.

2. Frontend API contract is inconsistent across major surfaces.
- `src/lib/api/api-client.ts:118` returns parsed JSON (not `Response`).
- Many callers still use `response.ok`, `response.json()`, `response.status`, etc. (for example `src/app/dashboard/debates/[id]/page.tsx:182`, `src/lib/api/debate-api.ts:95`, `src/lib/api/ipss-api.ts:133`, `src/app/dashboard/personas/page.tsx:75`).
- This breaks key user flows.

3. WebSocket message protocol is mismatched.
- Backend sends `initial_state` (`fastapi/app/services/debate_orchestrator.py:175`), while frontend listens for `debate_state` (`src/hooks/useDebateWebSocket.ts:124`).
- Frontend double-encodes WS payloads (`src/hooks/useDebateWebSocket.ts:192`, `src/hooks/useWebSocket.ts:122`).

4. Security/compliance posture is not enterprise-ready.
- SQL string interpolation is used in participants query (`fastapi/app/api/debate.py:404`).
- Memory manager states it is a minimal workaround and performs direct service-key inserts bypassing RLS (`fastapi/app/services/memory_manager.py:1`, `fastapi/app/services/memory_manager.py:23`).

5. Product completeness gaps in primary navigation.
- Sidebar includes routes that do not exist (`src/app/dashboard/layout.tsx:84`) for `/dashboard/models`, `/dashboard/analytics`, `/dashboard/settings`.

6. No OpenRouter BYOK implementation exists.
- No `openrouter` integration found in current codebase.

## 4) Product-level keep/kill/rebuild
### Keep
- Core positioning: multi-perspective AI decision debates.
- Role + persona abstraction.
- Document-grounded decisioning as a differentiator.
- Dark matte visual identity from dashboard.

### Kill (for V1)
- Voice mode.
- Multi-memory experimental layering exposed to users.
- Multiple provider-specific orchestration paths in one release.
- Non-essential advanced systems (DES/KDS/CBS/SIA) before core workflow is stable.

### Rebuild from scratch (recommended)
- Orchestration runtime.
- API contract and typed client layer.
- Authentication and tenant boundary model.
- Document pipeline and evidence/citation lifecycle.
- Admin, analytics, and settings surfaces.

## 5) Bottom line
The product idea is still valid, but the fastest path now is a **focused rebuild** using a simplified architecture, strict API contracts, and OpenRouter BYOK as the only model access path for launch.
