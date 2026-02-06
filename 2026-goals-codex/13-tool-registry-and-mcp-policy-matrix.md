# Tool Registry and MCP Policy Matrix (2026)

## Purpose
Define exactly which tools agents can call, under what conditions, and with what approval flow.

## 1) Core Policy Model
Every tool is registered with:
- `tool_id`
- `tool_name`
- `provider` (`internal|mcp`)
- `risk_tier` (`T0|T1|T2|T3`)
- `data_scope` (`public|internal|restricted`)
- `allowed_roles[]`
- `approval_mode` (`auto|host_approval|admin_approval`)
- `rate_limit`
- `timeout_ms`
- `audit_level` (`standard|verbose`)

Default:
- unregistered tools are blocked,
- tool calling is off unless explicitly enabled for workspace/debate/role.

## 2) Risk Tiers
### `T0` Read-only low-risk
- Example: math helper, formatter, local parser.
- Default approval: `auto`.

### `T1` External read-only retrieval
- Example: approved-domain web fetch, internal docs search.
- Default approval: `auto` with allowlist + budget.

### `T2` Sensitive read access / cross-system context
- Example: analytics warehouse query, CRM read.
- Default approval: `host_approval`.

### `T3` Write or high-impact actions
- Example: ticket creation, DB mutation, outbound messaging.
- Default approval: `admin_approval`.

## 3) MCP Server Governance
Each MCP server entry must include:
- `server_id`
- `server_name`
- `base_url`
- `owner_team`
- `status` (`approved|suspended|retired`)
- `allowed_tools[]`
- `secret_profile`
- `network_policy`

Rules:
- only approved MCP servers are callable,
- tools exposed by MCP must still be registered in Tool Registry,
- server-level and tool-level policy checks are both required.

## 4) Role Permission Matrix (Default)
### Host/Moderator Agent
- `T0`: allowed auto
- `T1`: allowed auto
- `T2`: allowed with host approval
- `T3`: denied by default

### Domain Specialist Agents (Engineer, Architect, Legal, Finance)
- `T0`: allowed auto
- `T1`: allowed auto (allowlist bound)
- `T2`: allowed with host approval
- `T3`: denied by default

### Research Analyst Agent
- `T0`: allowed auto
- `T1`: allowed auto (higher budget)
- `T2`: allowed with host approval
- `T3`: denied by default

### Observer/Review-only Agents
- `T0`: allowed auto
- `T1`: optional
- `T2/T3`: denied

## 5) Approval Workflow
1. Agent emits `tool_call_request`.
2. Policy engine evaluates:
- role permission,
- risk tier,
- data scope,
- budget/rate limits,
- workspace policy.
3. If approval needed:
- create pending approval item in host/admin queue.
4. On approval:
- execute via ToolGateway/MCP adapter.
5. Emit `tool_call_result` or `tool_call_denied`.

## 6) Budget and Guardrails
- `max_tool_calls_per_turn`
- `max_tool_calls_per_session`
- `max_external_requests_per_hour`
- `max_tool_runtime_ms`
- circuit-breaker thresholds per tool/server

Tool calls stop automatically when budget is exhausted unless user/admin extends.

## 7) Audit and Traceability
Every tool call must capture:
- `request_id`
- `debate_id`
- `agent_id`
- `tool_id`
- input hash + redacted payload
- output hash + redacted payload
- approval actor (if any)
- latency + status

Tool outputs used in final decisions must be referenceable in evidence map.

## 8) Security Controls
- tenant-scoped credentials,
- least-privilege secrets,
- no long-lived raw secrets in prompt context,
- output sanitization before model reinjection,
- deny-by-default egress for MCP servers.

## 9) Suggested V1 Tool Set
Start with low-risk tools:
1. `internal_doc_search` (`T1`)
2. `approved_web_fetch` (`T1`)
3. `table_calc_helper` (`T0`)
4. `citation_formatter` (`T0`)

Delay `T3` tools until post-beta.

## 10) Success Criteria
- > 99% tool calls attributable in audit logs.
- < 1% unauthorized tool attempts succeed (target: 0).
- Decision outputs include provenance for tool-derived claims.
- No cross-tenant leakage in tool or MCP execution paths.
