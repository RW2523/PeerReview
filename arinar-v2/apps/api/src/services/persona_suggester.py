"""
Persona Suggester
=================
Given a completed research profile, asks an LLM to suggest the most
appropriate AI committee personas for that specific research topic.

The output includes:
  - name          : e.g. "Dr. Elena Vasquez"
  - role          : committee role label
  - expertise     : specific expertise area relevant to the research
  - system_prompt : full persona instruction for the LLM
  - model_id      : model to use (set by reasoning mode)
  - focus_area    : the specific angle this persona will challenge

Each persona is distinct and stays in its lane (set by reasoning_modes).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from ..openrouter_client import OpenRouterClient
from .reasoning_modes import get_model, get_persona_model, ReasoningMode

COMMITTEE_ROLES = [
    "Advisor",
    "Methodology Professor",
    "Domain Expert",
    "Skeptical Reviewer",
    "Friendly Professor",
    "External Examiner",
]

_SYSTEM = """\
You are a graduate defense committee designer.
Given a research profile, suggest 6 realistic AI committee personas.
Each persona must be:
- A real-sounding academic with a name and institution
- Specifically matched to the research domain and methodology
- Assigned exactly one of the 6 committee roles provided
- Likely to ask questions UNIQUE to their role and expertise

Rules:
- Do not repeat expertise across personas
- Make each persona's focus_area directly relevant to the uploaded research
- system_prompt must be ≤ 120 words, written in first person, define their
  specific academic background, review style, and what they ALWAYS probe
- Return ONLY valid JSON — no markdown, no extra text
"""

_USER_TEMPLATE = """\
## Research Profile
Research problem: {research_problem}
Main claim:       {main_claim}
Methodology:      {methodology}
Domain:           {domain_hint}
Weak areas:       {weak_areas}

## Committee Roles to Assign (one per persona)
{roles}

---

Return a JSON array of exactly 6 objects, one per role, with EXACTLY these keys:
[
  {{
    "name":          "<First Last, Institution>",
    "role":          "<one of the 6 roles above>",
    "expertise":     "<specific expertise area — 1 sentence>",
    "focus_area":    "<what this persona will specifically probe in this research>",
    "system_prompt": "<first-person instruction — max 120 words>"
  }},
  ...
]
"""


def suggest_personas(
    research_profile: Dict[str, Any],
    openrouter_key: str,
    mode: ReasoningMode = "medium",
) -> List[Dict[str, Any]]:
    """
    Return a list of 6 suggested committee personas for the given research
    profile.  Each dict includes ``model_id`` set according to *mode*.
    """
    model_id = get_model("persona_suggestion", mode)

    # Build a domain hint from weak areas + methodology
    weak_areas = research_profile.get("weak_areas") or []
    if isinstance(weak_areas, str):
        try:
            weak_areas = json.loads(weak_areas)
        except Exception:
            weak_areas = []
    weak_str = ", ".join(
        w.get("area", "") for w in weak_areas if isinstance(w, dict)
    ) or "none identified"

    client = OpenRouterClient(api_key=openrouter_key)
    response = client.chat_completion(
        model=model_id,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": _USER_TEMPLATE.format(
                research_problem=research_profile.get("research_problem", ""),
                main_claim=research_profile.get("main_claim", ""),
                methodology=research_profile.get("methodology", ""),
                domain_hint=_infer_domain(research_profile),
                weak_areas=weak_str,
                roles="\n".join(f"{i+1}. {r}" for i, r in enumerate(COMMITTEE_ROLES)),
            )},
        ],
        temperature=0.6,
        max_tokens=2000,
    )

    raw = response["content"].strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*",     "", raw)
    raw = re.sub(r"```\s*$",     "", raw)
    personas: List[Dict] = json.loads(raw)
    if not isinstance(personas, list):
        personas = personas.get("personas", [])

    # Attach model_id per persona according to reasoning mode
    for p in personas:
        p["model_id"] = get_persona_model(p.get("role", ""), mode)

    return personas


def _infer_domain(profile: Dict) -> str:
    """Guess the research domain from methodology + problem keywords."""
    text = " ".join(filter(None, [
        profile.get("research_problem", ""),
        profile.get("methodology", ""),
        profile.get("main_claim", ""),
    ])).lower()

    domain_map = {
        "machine learning|deep learning|neural|transformer|llm|language model|nlp": "AI / Machine Learning",
        "federated|privacy|differential privacy|secure aggregation":             "Privacy-Preserving ML",
        "medical|clinical|patient|health|disease|biomedical":                    "Biomedical / Health Informatics",
        "database|query|sql|nosql|graph database|knowledge graph":               "Database Systems",
        "network|distributed|cloud|microservice|kubernetes":                     "Distributed Systems",
        "vision|image|object detection|segmentation|cnn":                        "Computer Vision",
        "robot|control|actuator|sensor|autonomous":                              "Robotics",
        "social|survey|interview|qualitative|grounded theory":                   "Social / HCI Research",
        "blockchain|smart contract|decentralized":                               "Blockchain",
        "security|attack|vulnerability|encryption|authentication":               "Cybersecurity",
    }
    for pattern, domain in domain_map.items():
        if re.search(pattern, text):
            return domain
    return "Computer Science / Engineering"
