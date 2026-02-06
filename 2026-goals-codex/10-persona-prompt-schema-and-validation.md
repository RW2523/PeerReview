# Persona Prompt Schema and Validation (2026)

## Purpose
Define a strict, auditable persona prompt model so every debate participant has:
- a consistent runtime identity,
- controllable behavior,
- editable prompt preview before launch,
- safe style-based simulation (including visionary-style templates).

Note:
- Persona prompt controls behavior.
- Agent continuity controls what knowledge is carried between meetings.

## 1) Persona Sources
Each participant persona can come from:
- `preset_template`
- `ai_generated_from_minimal_input`
- `custom_manual`

Preset library should include style-based profiles aligned with current assets:
- `Visionary Product Innovator (Steve Jobs style)`
- `Tech Entrepreneur (Elon Musk style)`
- other style profiles from the same library.

## 2) Canonical Persona Prompt Object
```json
{
  "persona_id": "uuid",
  "agent_id": "uuid",
  "agent_mode": "import_existing_agent",
  "source_mode": "preset_template",
  "name": "Visionary Product Innovator",
  "role_title": "Product Strategy Lead",
  "description": "User-experience-first product strategist with high quality bar.",
  "traits": {
    "temperament": "passionate",
    "communication": "direct",
    "decision_making": "principle_driven",
    "problem_solving": "first_principles",
    "agreeableness": 4,
    "openness": 9,
    "assertiveness": 8,
    "detail_orientation": 7,
    "creativity": 9
  },
  "behavior_policy": {
    "default_verbosity": "standard",
    "citation_required": true,
    "nudge_enabled": true,
    "internet_access_level": "limited"
  },
  "knowledge_policy": {
    "strict_epistemic": true,
    "allow_inference": false,
    "import_mode": "qa_ready_facts_only",
    "knowledge_confidence_threshold": 0.75
  },
  "system_prompt": "Final compiled prompt text",
  "user_overrides": {
    "instruction_patch": "Focus on practical trade-offs and avoid generic phrasing."
  },
  "version": 3,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

## 3) Prompt Compilation Pipeline
1. Load base template or generated draft.
2. Apply role title and debate objective context.
3. Apply trait-to-language mapping.
4. Apply user override patch.
5. Inject runtime policy block:
- verbosity defaults,
- citation rules,
- internet permission level,
- interaction etiquette (tag handling, rebuttal behavior).
6. Output compiled `system_prompt`.

## 4) Validation Rules
### Required fields
- `name`, `role_title`, `description`, `traits`, `behavior_policy`, `system_prompt`.

### Trait validation
- numeric traits in `1..10`.
- categorical traits must be from allowed enums.

### Prompt hygiene checks
- max prompt size (for example 8k chars).
- no unresolved placeholders.
- no conflicting directives (`always brief` + `always deep`).
- no forbidden content patterns by policy.

### Safety/compliance checks
- style-based simulation only, not identity impersonation claims.
- must include disclosure-safe language for public-figure-inspired templates.
- ensure policy-compatible internet/tool permissions.
- ensure agent-mode and knowledge-policy compatibility.

## 5) Pre-Meeting UX Contract
Before meeting start, user must be able to:
1. View persona card summary.
2. Open full prompt preview.
3. Edit prompt text and behavioral settings.
4. See validation warnings/errors inline.
5. Confirm and lock persona version for this debate.

The locked version is attached to debate session metadata.

## 6) Runtime Controls (During Debate)
- Host/user can override verbosity per turn (`brief|standard|deep_dive`).
- Host can toggle nudge allowance per participant.
- Internet permission can only be tightened at runtime by default.
- Any runtime override is event-logged with actor and timestamp.

## 7) Versioning and Audit
- Persona prompt versions are immutable snapshots once used in a live debate.
- Edits create new `version`.
- Audit record includes:
- old/new hash,
- editor actor,
- change summary,
- approval status.

## 8) AI-Generated Persona Flow (Minimal Input)
Minimal user inputs:
- target role title,
- one-line style brief,
- desired tone (`formal|balanced|aggressive|concise`),
- risk appetite (`low|medium|high`).

System generates draft:
- traits,
- description,
- behavior policy,
- full prompt.

User must approve/edit before launch.

## 9) Existing Codebase Alignment
Use and extend current persona foundation:
- API:
  - `fastapi/app/api/personas.py`
  - `src/lib/api/persona-api.ts`
- UI:
  - `src/components/personas/PersonaSelector.tsx`
  - `src/components/personas/PersonaEditor.tsx`
- Template content:
  - `Documents/ai-debate-roles.md`

## 10) Recommended API Additions
- `POST /api/personas/generate-draft`
- `POST /api/personas/compile-prompt`
- `POST /api/personas/validate-prompt`
- `POST /api/personas/{id}/versions`
- `GET /api/personas/{id}/versions`

## 11) Launch Gate
A debate cannot transition to `live` unless all participants pass:
- prompt validation,
- policy validation,
- model assignment validation,
- knowledge import validation (if `import_existing_agent`).
