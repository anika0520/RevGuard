"""Deterministic root-cause rules.

A rule cannot fire without evidence: every firing must attach the EvidenceItem ids
that caused it. The LLM never selects the cause -- it only explains this ranking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..models import CampaignHealthRecord, CauseCode, EvidencePackage

CAUSE_LABELS: dict[str, str] = {
    "TARGETING_RESTRICTION": "Targeting restriction",
    "SUPPLY_SHORTAGE": "Supply shortage",
    "VAST_PLAYBACK_ERRORS": "VAST playback errors",
    "GAM_COMPETITION": "GAM auction competition",
    "CREATIVE_ISSUE": "Creative issue",
    "FREQUENCY_CAP": "Frequency cap saturation",
    "BUDGET_PACING": "Overdelivery / budget pacing",
    "DATA_QUALITY": "Data quality failure",
}


@dataclass
class RuleHit:
    cause: CauseCode
    weight: float
    evidence_ids: list[str]
    explanation: str


@dataclass
class Rule:
    cause: CauseCode
    when: Callable[[CampaignHealthRecord], bool]
    weight: Callable[[CampaignHealthRecord], float]
    metrics: list[str]
    explain: Callable[[CampaignHealthRecord], str]


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


RULES: list[Rule] = [
    Rule(
        cause="TARGETING_RESTRICTION",
        when=lambda r: r.eligible_inventory_change_pct <= -15.0 or r.targeting_changed_recently,
        weight=lambda r: _clamp(
            abs(min(0.0, r.eligible_inventory_change_pct)) / 40.0
            + (0.35 if r.targeting_changed_recently else 0.0)
        ),
        metrics=["eligible_inventory", "targeting_change", "fill_rate"],
        explain=lambda r: (
            f"Eligible inventory contracted {r.eligible_inventory_change_pct:.1f}%"
            + (" following a recent targeting change" if r.targeting_changed_recently else "")
        ),
    ),
    Rule(
        cause="SUPPLY_SHORTAGE",
        when=lambda r: r.fill_deviation_pct <= -20.0 or r.fill_z_score <= -2.5,
        weight=lambda r: _clamp(abs(min(0.0, r.fill_deviation_pct)) / 40.0),
        metrics=["fill_rate", "eligible_inventory"],
        explain=lambda r: (
            f"Fill rate fell {abs(r.fill_deviation_pct):.1f}% below its "
            f"{r.baseline_fill_rate:.1f}% baseline"
        ),
    ),
    Rule(
        cause="VAST_PLAYBACK_ERRORS",
        when=lambda r: (
            r.baseline_error_rate > 0 and r.error_rate >= 2.0 * r.baseline_error_rate
        ),
        weight=lambda r: _clamp(
            (r.error_rate / max(1e-6, r.baseline_error_rate)) / 5.0
        ),
        metrics=["error_rate", "vast_error_code"],
        explain=lambda r: (
            f"VAST errors are running {r.error_rate / max(1e-6, r.baseline_error_rate):.1f}x "
            f"baseline, concentrated on {r.worst_platform} ({r.worst_vast_code})"
        ),
    ),
    Rule(
        cause="GAM_COMPETITION",
        when=lambda r: r.auction_pressure_change_pct >= 20.0,
        weight=lambda r: _clamp(r.auction_pressure_change_pct / 50.0),
        metrics=["auction_pressure", "fill_rate"],
        explain=lambda r: (
            f"Auction pressure from competing line items rose "
            f"{r.auction_pressure_change_pct:.1f}%"
        ),
    ),
    Rule(
        cause="FREQUENCY_CAP",
        when=lambda r: r.unique_reach_saturation >= 0.85,
        weight=lambda r: _clamp((r.unique_reach_saturation - 0.7) / 0.3),
        metrics=["reach_saturation", "eligible_inventory"],
        explain=lambda r: (
            f"Unique-reach saturation at {r.unique_reach_saturation * 100:.0f}% is throttling "
            f"addressable delivery"
        ),
    ),
    Rule(
        cause="CREATIVE_ISSUE",
        when=lambda r: r.creative_error_share >= 0.4 and r.error_deviation_pct >= 50.0,
        weight=lambda r: _clamp(r.creative_error_share),
        metrics=["creative_error_share", "error_rate"],
        explain=lambda r: (
            f"{r.creative_error_share * 100:.0f}% of playback errors trace to one creative"
        ),
    ),
    Rule(
        cause="BUDGET_PACING",
        when=lambda r: r.pacing_pct > 130.0,
        weight=lambda r: _clamp((r.pacing_pct - 100.0) / 60.0),
        metrics=["pacing_pct", "delivery_pct"],
        explain=lambda r: (
            f"Campaign is overdelivering at {r.pacing_pct:.0f}% of the required rate and will "
            f"exhaust its goal early"
        ),
    ),
    Rule(
        cause="DATA_QUALITY",
        when=lambda r: r.data_quality.verdict == "BAD",
        weight=lambda r: _clamp(1.0 - r.data_quality.score + 0.5),
        metrics=["data_quality"],
        explain=lambda r: (
            f"Feed integrity checks failed: {', '.join(r.data_quality.failed_checks)}"
        ),
    ),
]


def evaluate(record: CampaignHealthRecord, package: EvidencePackage) -> list[RuleHit]:
    by_metric = {item.metric: item.id for item in package.items}
    hits: list[RuleHit] = []
    for rule in RULES:
        if not rule.when(record):
            continue
        evidence_ids = [by_metric[m] for m in rule.metrics if m in by_metric]
        if not evidence_ids:
            continue  # no evidence -> the rule is not allowed to fire
        weight = round(rule.weight(record), 4)
        if weight <= 0.01:
            continue
        hits.append(
            RuleHit(
                cause=rule.cause,
                weight=weight,
                evidence_ids=evidence_ids,
                explanation=rule.explain(record),
            )
        )
    return sorted(hits, key=lambda h: h.weight, reverse=True)
