# Agent Continuity and Knowledge Transfer (2026)

## Purpose
Define how agents persist across meetings like humans with memory, while enforcing strict epistemic boundaries:
- agents can reuse prior knowledge,
- agents only state what they know from evidence,
- no silent assumptions.

## 1) Core Model
Separate these concepts:
- `Persona`: behavior/style template.
- `Agent`: persistent identity used across meetings.
- `Participant`: an agent instance in one specific meeting.

This enables one software engineer agent to appear in many meetings and retain learned context.

## 2) Meeting Start Options for Participants
When adding a participant, user chooses one mode:
1. `new_agent`:
- fresh agent identity, no prior knowledge memory.
2. `import_existing_agent`:
- reuse prior agent with selected knowledge scope.
3. `clone_persona_only`:
- copy behavior template but do not import learned knowledge.

## 3) Knowledge Import Controls
For `import_existing_agent`, user configures:
- source meetings (all vs selected),
- time range,
- confidentiality filter,
- minimum confidence threshold,
- import mode:
  - `full_import`
  - `summary_only`
  - `qa_ready_facts_only`

## 4) Knowledge Units (What an Agent “Knows”)
Store transferable knowledge as explicit units:
- `knowledge_id`
- `agent_id`
- `statement`
- `knowledge_type` (`fact|decision|constraint|definition|dependency`)
- `source_event_ids[]`
- `source_document_ids[]`
- `confidence`
- `learned_at`
- `expires_at` (optional)

Only these units are eligible for cross-meeting reuse.

## 5) No-Assumptions Response Policy
Default enterprise mode: `strict_epistemic`.

Rules:
- Agent may assert only knowledge with source-backed evidence.
- If evidence is missing, agent must respond with:
  - `unknown`, or
  - `needs_clarification`, or
  - `needs_research` (if allowed by policy).
- Inferred content must be explicitly labeled as inference.
- Unlabeled assumptions are disallowed.

## 6) Example Flow (Architect -> Engineer -> PM)
Meeting 1:
- Architect explains system design to Engineer.
- Platform stores Engineer `knowledge_units` with links to architect messages/docs.

Meeting 2:
- PM asks Engineer an architecture question.
- Engineer retrieves only its own valid knowledge units.
- Engineer answers from those units and cites source references.
- If gaps exist, Engineer says what is unknown instead of guessing.

## 7) Runtime Retrieval Contract for Agent Answers
Before generating answer:
1. Resolve `agent_id`.
2. Fetch agent-scoped knowledge units for current workspace.
3. Apply confidence and recency policy.
4. Build answer context from valid units only.
5. Enforce no-assumption validator before publishing message.

## 8) Knowledge Transfer Events
Add events to event ledger:
- `knowledge_learned`
- `knowledge_validated`
- `knowledge_imported`
- `knowledge_rejected`
- `knowledge_expired`

These events must be auditable.

## 9) Data Model Additions
- `agents`
- `agent_versions`
- `agent_knowledge_units`
- `agent_meeting_links`
- `knowledge_evidence_edges`

All tables are tenant/workspace scoped.

## 10) API Additions
- `POST /api/agents`
- `GET /api/agents`
- `POST /api/agents/{id}/import-knowledge`
- `GET /api/agents/{id}/knowledge`
- `POST /api/agents/{id}/knowledge/validate`
- `POST /api/debates/{id}/participants/import-agent`

## 11) UX Requirements
In participant setup:
- show “New Agent / Import Existing Agent / Clone Persona Only”.
- if importing, show knowledge preview and confidence summary.
- show what will be carried and what will be excluded.

In live room:
- answer card includes `Known From` references.
- if unknown, show explicit `Not in agent knowledge` indicator.

## 12) Governance and Safety
- Respect data boundaries between workspaces and confidentiality levels.
- Prevent knowledge leakage from restricted meetings.
- Maintain full audit trails for imports and reused knowledge.
- Allow admin revocation/erase of agent knowledge.
