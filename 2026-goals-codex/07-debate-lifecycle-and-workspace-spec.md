# Debate Lifecycle and Workspace Spec (2026)

## Goal
Define the full product flow from debate creation to real-time execution, so the team can build a consistent enterprise-ready experience.

## 1) Debate Creation Flow (User Journey)
### Step 1: Define the problem
User enters:
- `debate_title`
- `problem_statement` (required)
- `desired_outcome` (decision, recommendation, plan, risk memo, etc.)
- `decision_deadline` (optional)
- `debate_mode` (`quick`, `standard`, `deep`)
- `meeting_timebox_minutes` (for example 15/30/45/60)
- `auto_end_behavior` (`host_suggest`, `hard_stop`, `user_only`)
- `modality` (`text_only|voice_only|hybrid`)

### Step 2: Attach context files
User uploads one or more files:
- PDFs, docs, spreadsheets, links, notes.
- System runs ingestion and marks each file as:
  - `processing`
  - `ready`
  - `failed`
- Debate can start with partial readiness, but all `ready` files are shared to every agent.
- Each agent receives a common material index and can cite those materials during turns.

### Step 3: Choose participants
User selects participants (3-8 active for V1, up to 12 total including review-only roles):
- Each participant has:
  - `display_name`
  - `role_title` (CTO, CFO, Legal Counsel, PC Hardware Expert, etc.)
  - `persona_profile` (tone, constraints, expertise, risk appetite)
  - `model_config` (OpenRouter model + temperature + token caps)

Persona source options per participant:
- `preset_template`: load from system persona library.
- `ai_generated`: user provides minimal input and AI drafts persona.
- `custom_manual`: user builds persona from scratch.

Agent continuity options per participant:
- `new_agent`: start fresh with no prior knowledge.
- `import_existing_agent`: carry selected prior meeting knowledge.
- `clone_persona_only`: same persona behavior, no knowledge carry-over.

Preset library must include style-based simulated visionaries from existing assets:
- `Visionary Product Innovator (Steve Jobs style)`.
- `Tech Entrepreneur (Elon Musk style)`.
- Additional style profiles from the same template pack.

### Step 4: Assign model per participant
Each role is powered independently:
- One role can use `openai/*`, another `anthropic/*`, etc. through OpenRouter.
- Each role becomes an independent agent runtime instance after launch.

### Step 4A: Persona prompt preview and fine-tune
Before launch, user can inspect each participant's generated runtime prompt:
- system persona prompt,
- role constraints,
- response style defaults,
- citation behavior.

User can edit prompt text before starting debate.
The final prompt version is versioned and audit logged.
Imported-agent knowledge preview is shown alongside prompt preview.

### Step 4B: Tool permissions and internet research policy
Per participant, user configures:
- internet access (`off|limited|enabled`),
- allowed domains (optional allowlist),
- research budget (requests/time/token limits),
- approval mode (`auto` or `human_approval_required`).
- tool calling permission (`off|approved_tools_only`).
- optional MCP scope (which approved MCP servers/tools are allowed).

### Step 5: Design discussion order
User sets discussion structure:
- `turn_order_type`:
  - `round_robin`
  - `weighted_priority`
  - `moderator_directed`
  - `custom_graph` (advanced)
- Optional constraints:
  - max turns per participant
  - mandatory first speaker
  - required legal/finance review before close
  - host approval required for off-order turns

### Step 6: Review and launch
User confirms:
- problem + goal
- files + readiness state
- participants + models
- persona prompts + persona source
- research permissions per participant
- flow order
- cost guardrails

Then presses `Start Debate`.

### Step 7: Optional hot-join setup
User may enable `allow_hot_join_participants` before launch:
- If enabled, new participants can be added during `live` state.
- System creates a catch-up summary and context bootstrap for the new agent.

## 2) Agent Runtime Semantics
When debate starts, each participant becomes:
- a scoped agent with its own role instructions,
- access to shared debate context,
- controlled access to memory fabric and evidence context,
- policy-limited model execution (BYOK + org policy).

Each agent loop:
1. Receive context packet.
2. Generate argument/rebuttal/question.
3. Attach evidence/citations when applicable.
4. Emit message event to room feed.
5. Update memory and state projections.

Adaptive behavior requirement:
- Agents should autonomously decide when to answer briefly vs deeply.
- Agents can request an off-order response when they detect urgency/relevance.
- Human can override verbosity and priority at any time.
- Agents must answer from known, source-backed knowledge only by default.
- If knowledge is missing, agents should explicitly return unknown/needs clarification.

## 3) Workspace UX (Slack-like Discussion Room)
### Layout
1. Left rail:
- Workspaces
- Debate rooms
- Saved templates

2. Center feed:
- Real-time threaded debate messages
- Agent role chips and model chip per message
- Citation badges and expandable source snippets

3. Right panel:
- Participants list with status (`thinking`, `responding`, `idle`, `blocked`)
- Active turn order map
- Live summary + unresolved questions

4. Top bar:
- Debate title/status
- timer and token/cost meter
- `Intervene` button

### Message behaviors
- Agents can tag other agents: `@Legal`, `@CTO`, `@Finance`.
- Humans can tag agents mid-stream.
- Threads supported for side debates.
- Pin message as “Decision Candidate” or “Risk Flag”.
- Agents may send a pre-turn nudge to host requesting early response rights.

## 4) Human-in-the-Loop Controls
### Intervention actions
User can:
- pause/resume discussion,
- redirect topic,
- ask a targeted question to one or many tagged agents,
- request evidence on a claim,
- ask for clarifications,
- force a rebuttal cycle before decision close.
- end meeting immediately (`End Now`) at any point.

### Intervention flow
1. User presses `Intervene`.
2. Composer opens with intervention mode.
3. User tags specific agents (`@CFO @Legal`).
4. User chooses intervention intent:
- `clarify`
- `challenge`
- `re-scope`
- `request-evidence`
- `decision-check`
5. System injects intervention event with high priority in queue.

## 5) Real-time Discussion Modes
- `Open discussion`: free-form with soft turn guidance.
- `Structured debate`: strict turn order.
- `Cross-examination`: selected agents must challenge a prior claim.
- `Decision synthesis`: host agent summarizes options and asks final objections.

## 6) Timeboxing and Ending Rules
- Every debate has a meeting timebox.
- Host warns at configurable thresholds (`T-10`, `T-5`, `T-1` minutes).
- On timeout:
  - `host_suggest`: host prompts close vs extend.
  - `hard_stop`: system moves to synthesis automatically.
  - `user_only`: continues until user ends manually.
- Human moderator can always end immediately.

## 7) End-of-Debate Outputs
When user ends debate, system produces:
- decision summary,
- executive summary,
- minutes of meeting,
- alternatives considered,
- dissent notes,
- risk register,
- action plan,
- action items with owners and deadlines,
- evidence map (claim -> source).

All outputs must include traceable references to room events and files.

## 8) Product Requirements (V1)
### Functional
- Debate can be created from problem + files + participants + model mapping.
- Per-role model assignment is configurable.
- Persona templates, AI-generated personas, and custom personas are all supported.
- Persona runtime prompt is previewable and editable before launch.
- Agent continuity mode (new/import/clone persona-only) is configurable per participant.
- Human can intervene anytime with agent tagging.
- Live room supports real-time multi-agent messaging.
- Decision outputs are exportable.
- Human can end debate instantly.
- Materials uploaded pre-meeting are available to all agents.
- Agents can request host-approved off-order turns.
- Internet research is policy-controlled per participant.
- Voice/hybrid modality is supported through the same core debate flow.
- Future tool calling can be enabled per participant via policy.
- Imported-agent answers are provenance-backed and assumption-safe.

### Non-functional
- P95 message round-trip latency target defined by environment.
- Replayable event history.
- Tenant-isolated memory and retrieval.
- Full audit trail for interventions and model calls.
- Host pre-turn nudge arbitration target: sub-second path, with in-memory decisioning.

## 9) Example Use Cases
### A) Laptop purchase debate (consumer/professional)
- Roles: PC Hardware Expert, Budget Analyst, Power User, IT Support.
- Output: ranked recommendation with trade-offs and final pick.

### B) Startup go-to-market plan
- Roles: CEO, CTO, CMO, Finance Lead, Customer Research Lead.
- Output: 90-day strategy with risks and milestones.

### C) Legal matter pre-analysis
- Roles: Legal Counsel, Compliance Officer, Operations, Risk Analyst.
- Output: issue framing, risk matrix, recommended actions, open legal questions.

## 10) UI Style Constraint
This workflow must inherit Arinar’s dark matte system from:
- `03-dark-matte-design-system.md`

No bright/light-mode-first workspace shell for core debate surfaces.

## 11) Critical Open Decisions (Must Finalize Before Build)
- Final participant hard cap for GA (keep 12 or reduce for reliability).
- Default internet policy for enterprise tenants (`off` recommended).
- Who can approve research requests (workspace admin vs meeting host).
- Persona legal/compliance guidelines for public-figure-inspired style templates.
- Default action-item owner model (human assignee required vs agent suggestion only).
- Export formats for minutes/action items (PDF, DOCX, API payload).
