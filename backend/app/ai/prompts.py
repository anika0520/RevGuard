"""Versioned prompts and the strict output schema the model must return."""

from __future__ import annotations

import json

from ..models import CandidateCause, EvidencePackage

PROMPT_VERSION = "diagnosis.v3"

SYSTEM_PROMPT = """You are an advertising operations diagnostic analyst.

You will receive a structured EVIDENCE PACKAGE and a RANKED LIST OF CANDIDATE CAUSES
that were produced by a deterministic analytics engine.

Your job is to SYNTHESIZE, not to speculate.

Rules:
- Use ONLY the numbers present in the evidence package.
- Every claim you make must cite an evidence id, e.g. [EV-03].
- Do NOT invent metrics, dates, platforms, or percentages.
- Do NOT change the ranking of causes. Explain the ranking you were given.
- If the evidence is insufficient for a confident diagnosis, say so explicitly and set
  "insufficient_evidence": true.
- Write for a busy Ad Ops manager: direct, specific, no filler, no marketing language.

Return ONLY valid JSON matching this schema:
{
  "narrative": "2-4 sentences. Every claim cites [EV-xx].",
  "primary_cause_explanation": "one sentence",
  "secondary_notes": ["string"],
  "recommended_action_summary": "one sentence",
  "evidence_cited": ["EV-03", "EV-07"],
  "insufficient_evidence": false
}"""

OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "narrative",
        "primary_cause_explanation",
        "secondary_notes",
        "recommended_action_summary",
        "evidence_cited",
        "insufficient_evidence",
    ],
    "properties": {
        "narrative": {"type": "string"},
        "primary_cause_explanation": {"type": "string"},
        "secondary_notes": {"type": "array", "items": {"type": "string"}},
        "recommended_action_summary": {"type": "string"},
        "evidence_cited": {"type": "array", "items": {"type": "string"}},
        "insufficient_evidence": {"type": "boolean"},
    },
}


def build_user_prompt(package: EvidencePackage, causes: list[CandidateCause]) -> str:
    evidence = [
        {
            "id": i.id,
            "metric": i.metric,
            "statement": i.label,
            "current": i.current_value,
            "baseline": i.baseline_value,
            "delta_pct": i.delta_pct,
            "z_score": i.z_score,
            "source": i.source,
            "window": i.window,
            "strength": i.strength,
        }
        for i in package.items
    ]
    ranked = [
        {
            "rank": n + 1,
            "cause": c.cause,
            "label": c.label,
            "confidence": c.confidence,
            "evidence_ids": c.evidence_ids,
            "engine_note": c.explanation,
        }
        for n, c in enumerate(causes)
    ]
    return json.dumps(
        {
            "campaign": package.campaign_name,
            "campaign_id": package.campaign_id,
            "window": package.window,
            "evidence_package": evidence,
            "ranked_candidate_causes": ranked,
        },
        indent=2,
        default=str,
    )


COPILOT_SYSTEM_PROMPT = """You are Guardian Copilot, an ad operations assistant.

Answer using ONLY the JSON context provided. Cite campaign ids and exact figures from
the context. If the context does not contain the answer, say so plainly. Be concise:
two or three sentences, no preamble."""
