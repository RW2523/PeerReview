# Agent Participation and Turn Policy (2026)

## Purpose
Lock down practical limits and runtime behavior for multi-agent debates in a Slack-style workspace.

## 1) Participation Limits
- Recommended active agents: `3-8`.
- Upper bound for V1: `12` total participants (including review-only roles).
- If above 8 active, enforce stricter turn and token budgets.

## 2) Per-Agent Runtime Budgets
- First token target: `1-3s`.
- Typical turn completion target: `6-20s`.
- Hard timeout: `30s`, then retry/fallback policy.
- Per-turn token budgets by mode:
  - `quick`: `80-150`
  - `standard`: `150-350`
  - `deep`: `350-800`

## 3) Response Shape in Slack UI
Every agent message should use:
- short top-line answer,
- optional detailed block,
- citations when needed.

Default UX rule:
- concise by default,
- expandable detail on demand.

## 4) Adaptive Verbosity (Agent Autonomy + User Control)
Agent autonomy:
- Agent decides brief vs detailed using:
  - complexity of question,
  - risk level,
  - evidence availability,
  - whether directly tagged.

User/host overrides:
- `@Agent brief`
- `@Agent standard`
- `@Agent deep_dive`
- Host can cap verbosity globally for timeboxed sessions.

## 5) Participant Awareness Model
Each turn context packet must include:
- participant roster (name, role, model),
- current speaking order,
- latest key points per participant,
- unresolved questions and objections.

This ensures each agent knows who is in room and can coordinate naturally.

## 6) Pre-turn Nudge Mechanism
Agents can request to speak early before their turn:
- send `pre_turn_nudge` with rationale,
- host approves/rejects quickly,
- approved nudges get temporary queue priority.

Latency target:
- host arbitration path in near real-time (`100-400ms` normal load target).

## 7) Adding Participants Mid-Debate
Allowed in `live` state if workspace policy permits.

Hot-join sequence:
1. Pause or soft-pause queue.
2. Add participant role/model.
3. Generate catch-up summary + context bootstrap.
4. Insert participant into updated turn order.
5. Resume and audit-log change event.

Restrictions:
- No hot-join during `synthesis`/`closed`.
- Optional admin-only role addition in enterprise plans.

## 8) Timebound Meeting Controls
- Debate includes `meeting_timebox_minutes`.
- Host emits warnings at `T-10`, `T-5`, `T-1`.
- End modes:
  - `host_suggest`
  - `hard_stop`
  - `user_only`
- Human can always end immediately.

## 9) Mandatory End Package
When debate ends, system auto-generates:
- executive summary,
- minutes of meeting,
- action items with owners and due dates,
- risks and dissent notes,
- evidence map (claim -> source),
- unresolved questions.

## 10) Pre-uploaded Materials Policy
Before start, user can upload files and notes.

Material handling:
- all ready materials are available to all agents,
- agents retrieve only relevant chunks per turn,
- citations must refer to material IDs and snippets,
- memory stores extracted insights for later turns and post-session recall.

## 11) Internet Access and Verification Policy
Default:
- Internet research is disabled.

Enablement model:
- Configurable per workspace, debate, and participant.
- Permission levels:
  - `off`: no external calls.
  - `limited`: allow gateway search/fetch with strict allowlist and low budgets.
  - `enabled`: full policy-guarded research access.

Enforcement:
- All internet operations run through backend research gateway.
- Domain allowlist/denylist and budget limits are mandatory.
- Optional human approval gate before execution.
- All external claims must include URL/source citations.

## 12) Persona Template and Creation Workflow
Persona source modes:
- `preset_template`
- `ai_generated_from_minimal_input`
- `custom_manual`

Pre-meeting persona UX:
1. User selects a preset or provides minimal brief.
2. System generates full persona profile + runtime prompt.
3. User sees full prompt and config preview.
4. User edits and confirms before meeting start.

Required per-agent persona fields:
- identity (name/title/role),
- behavioral traits,
- communication style,
- reasoning and citation behavior,
- role compatibility constraints.

## 13) Existing Codebase Alignment (Carry Forward)
Current project already has persona infrastructure and should be reused:
- Persona API surface:
  - `fastapi/app/api/personas.py`
  - `src/lib/api/persona-api.ts`
- Persona UI/editor components:
  - `src/components/personas/PersonaSelector.tsx`
  - `src/components/personas/PersonaEditor.tsx`
- Style-based simulated visionary profiles:
  - `Documents/ai-debate-roles.md` (includes Steve Jobs style and Elon Musk style profiles).

## 14) Agent Continuity Modes Across Meetings
Per participant, user chooses:
- `new_agent`
- `import_existing_agent`
- `clone_persona_only`

Import mode options:
- `full_import`
- `summary_only`
- `qa_ready_facts_only`

## 15) Epistemic Guardrail: Only What Agent Knows
Default enterprise setting should enforce:
- answers from source-backed agent knowledge only,
- no unstated assumptions,
- explicit unknown response when evidence is missing,
- inference must be labeled as inference.
