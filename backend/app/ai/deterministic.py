"""Deterministic synthesis -- the fallback that keeps the demo alive with no API key.

It builds the narrative by stitching together verbatim evidence statements, so every
number it emits is grounded by construction.
"""

from __future__ import annotations

import json
from typing import Any


def _statements(evidence: list[dict[str, Any]]) -> dict[str, str]:
    return {e["id"]: e["statement"] for e in evidence}


def synthesize(payload: dict[str, Any]) -> dict[str, Any]:
    evidence = payload.get("evidence_package", [])
    causes = payload.get("ranked_candidate_causes", [])
    stmt = _statements(evidence)
    order = [e["id"] for e in evidence]

    if not causes:
        return {
            "narrative": (
                "No candidate cause met its evidence threshold. Delivery is within the "
                "expected operating envelope for this campaign."
            ),
            "primary_cause_explanation": "No dominant cause identified.",
            "secondary_notes": [],
            "recommended_action_summary": "No action required. Continue monitoring.",
            "evidence_cited": order[:1],
            "insufficient_evidence": True,
        }

    primary = causes[0]
    secondary = causes[1:3]
    cited: list[str] = []
    parts: list[str] = []

    lead = next((i for i in order if i in stmt and "pacing" in _metric(evidence, i)), order[0])
    parts.append(f"{stmt[lead]} [{lead}].")
    cited.append(lead)

    p_ids = [i for i in primary.get("evidence_ids", []) if i in stmt and i != lead][:2]
    if p_ids:
        detail = " ".join(f"{stmt[i]} [{i}]." for i in p_ids)
        parts.append(
            f"The dominant contributor is {primary['label'].lower()} "
            f"({primary['confidence'] * 100:.0f}% of weighted evidence). {detail}"
        )
        cited.extend(p_ids)

    for n, c in enumerate(secondary):
        s_ids = [i for i in c.get("evidence_ids", []) if i in stmt and i not in cited][:1]
        if s_ids:
            lead_in = "A secondary factor is" if n == 0 else "A third contributor is"
            parts.append(
                f"{lead_in} {c['label'].lower()} "
                f"({c['confidence'] * 100:.0f}%): {stmt[s_ids[0]]} [{s_ids[0]}]."
            )
            cited.extend(s_ids)

    delivery = next((i for i in order if _metric(evidence, i) == "delivery_pct"), None)
    if delivery and delivery not in cited:
        parts.append(
            f"Cumulative delivery still reads within tolerance -- {stmt[delivery]} [{delivery}] "
            f"-- which is precisely why a rate-based problem like this is missed by manual review."
        )
        cited.append(delivery)

    return {
        "narrative": " ".join(parts),
        "primary_cause_explanation": (
            f"{primary['label']}: {primary.get('engine_note', '')}".strip().rstrip(".") + "."
        ),
        "secondary_notes": [
            f"{c['label']}: {c.get('engine_note', '')}".strip().rstrip(".") + "."
            for c in secondary
        ],
        "recommended_action_summary": _action_summary(primary["cause"], payload),
        "evidence_cited": list(dict.fromkeys(cited)),
        "insufficient_evidence": False,
    }


def _metric(evidence: list[dict[str, Any]], eid: str) -> str:
    for e in evidence:
        if e["id"] == eid:
            return str(e.get("metric", ""))
    return ""


ACTION_SUMMARY = {
    "TARGETING_RESTRICTION": "Relax the most restrictive targeting dimension to restore eligible inventory.",
    "SUPPLY_SHORTAGE": "Add or re-weight supply partners to rebuild fill.",
    "VAST_PLAYBACK_ERRORS": "Pause the worst-offending tags and investigate VAST compatibility on the affected platform.",
    "GAM_COMPETITION": "Raise line item priority to win back auction share.",
    "FREQUENCY_CAP": "Loosen the frequency cap to expand addressable reach.",
    "CREATIVE_ISSUE": "Replace or re-transcode the failing creative.",
    "BUDGET_PACING": "Throttle delivery so the goal is not exhausted before flight end.",
    "DATA_QUALITY": "Do not action delivery. Investigate the ingestion pipeline first.",
}


def _action_summary(cause: str, payload: dict[str, Any]) -> str:
    return ACTION_SUMMARY.get(cause, "Investigate before taking action.")


def answer_question(user: str) -> str:
    """The route precomputes a grounded answer; a real LLM would rewrite the same context."""
    try:
        ctx = json.loads(user)
    except json.JSONDecodeError:
        return "I can only answer from the monitoring context provided."
    return ctx.get("deterministic_answer") or "I do not have that in the current context."
