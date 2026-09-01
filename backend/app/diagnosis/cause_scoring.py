"""Normalize rule weights into cause confidences, and derive an overall confidence.

Confidence means "how strongly the available evidence supports this diagnosis" --
not "how sure the language model feels".
"""

from __future__ import annotations

from ..models import CandidateCause, ConfidenceContribution, EvidencePackage
from .root_cause_rules import CAUSE_LABELS, RuleHit

STRENGTH_VALUE = {"STRONG": 0.40, "MODERATE": 0.25, "WEAK": 0.10}


def rank(hits: list[RuleHit]) -> list[CandidateCause]:
    total = sum(h.weight for h in hits)
    if total <= 0:
        return []
    return [
        CandidateCause(
            cause=h.cause,
            label=CAUSE_LABELS.get(h.cause, h.cause),
            weight=h.weight,
            confidence=round(h.weight / total, 4),
            evidence_ids=h.evidence_ids,
            explanation=h.explanation,
        )
        for h in hits
    ]


def overall_confidence(
    causes: list[CandidateCause], package: EvidencePackage
) -> tuple[float, list[ConfidenceContribution]]:
    """Sum the strength of the evidence actually cited by the ranked causes, capped at 0.97."""
    if not causes:
        return 0.0, []
    cited = {eid for c in causes for eid in c.evidence_ids}
    by_id = {item.id: item for item in package.items}
    contributions: list[ConfidenceContribution] = []
    running = 0.0
    for eid in sorted(cited):
        item = by_id.get(eid)
        if not item:
            continue
        value = STRENGTH_VALUE[item.strength]
        running += value
        contributions.append(
            ConfidenceContribution(label=f"{item.label} [{eid}]", contribution=round(value, 3))
        )
    contributions.sort(key=lambda c: c.contribution, reverse=True)
    contributions = contributions[:5]
    total = sum(c.contribution for c in contributions)
    confidence = round(min(0.97, total), 3)
    contributions.append(
        ConfidenceContribution(label="Evidence-support total", contribution=confidence)
    )
    return confidence, contributions
