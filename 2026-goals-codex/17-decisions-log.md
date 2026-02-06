# 17 - Decisions Log

Date initialized: 2026-02-06  
Purpose: single source of truth for product/architecture decisions so they are not re-debated across docs/tickets.

## How To Use
- Add one row per decision.
- Do not edit history silently. Add a new row when changing a prior decision.
- Every ticket should reference this file for open decisions.

## Decision Table
| Decision | Options | Chosen | Date | Rationale |
|---|---|---|---|---|
| Model provider policy | OpenRouter-only / direct SDK mix | OpenRouter-only | 2026-02-06 | BYOK requirement, provider abstraction, enterprise policy control. |
| Debate ID format | UUID v4 / ULID / nanoid | UUID v4 | 2026-02-06 | Standard format, contract consistency, easy tooling support. |
| Timestamp format | UTC ISO-8601 / local timezone | UTC ISO-8601 | 2026-02-06 | Consistent audit logs and cross-region correctness. |
| Event pagination | Cursor / offset | Cursor | 2026-02-06 | Stable realtime/event ledger pagination. |
| Default internet policy | Off / limited / on | Off | 2026-02-06 | Enterprise-safe default; allow explicit opt-in later. |
| Runtime DB access | Direct DB / MCP-only DB | Direct DB | 2026-02-06 | Reliability and performance for core app runtime. |
| Agent data-tooling access | None / MCP optional | MCP optional | 2026-02-06 | Future tool-calling path without coupling runtime to MCP. |
| Local infra stack | Plain Postgres / Supabase local | Supabase local | 2026-02-06 | Faster enterprise-aligned local platform bootstrap. |
| Backend framework baseline | FastAPI / Next-only API | FastAPI | 2026-02-06 | Aligns with existing workspace boundaries and orchestration needs. |
| Participant cap (active) | 6 / 8 / 12 | 8 | 2026-02-06 | Keeps coordination latency manageable while supporting real debates. |
| Participant cap (observer) | 0 / 12 / 20 | 12 | 2026-02-06 | Supports review without overwhelming active turn flow. |
| Meeting hard timebox | Optional / required default | Optional with default enabled | 2026-02-06 | Safety + control while allowing manual override. |

## Open Decisions
| Decision | Owner | Due | Notes |
|---|---|---|---|
| Staging/production Supabase project details | Founder | Before staging | Project URL, anon key, service role key, DB connection string. |
| First GA model allowlist | Founder | Before M2 complete | Which OpenRouter model IDs are allowed by default. |
| Data retention defaults per tenant tier | Founder | Before enterprise pilot | Event ledger retention and deletion rules. |

