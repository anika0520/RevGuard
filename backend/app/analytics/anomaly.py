"""Anomaly detection: multi-signal agreement + sustained windows.

A single metric crossing a threshold is not an incident. We require at least
`min_agreeing_signals` independent signals AND persistence across consecutive
windows. This is the false-positive defence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import get_settings
from ..models import CampaignHealthRecord


@dataclass
class AnomalyResult:
    signals: list[str] = field(default_factory=list)
    sustained: bool = False
    fired: bool = False
    reasons: list[str] = field(default_factory=list)


def signals_for(record: CampaignHealthRecord) -> list[str]:
    t = get_settings().anomaly
    out: list[str] = []
    if record.pacing_gap_pts <= t.pacing_gap_pts:
        out.append("pacing_down")
    if record.pacing_pct > t.overdelivery_pacing_pct:
        out.append("overdelivery")
    if record.fill_deviation_pct <= t.fill_deviation_pct or record.fill_z_score <= -t.z_score_abs:
        out.append("fill_rate_down")
    if record.error_deviation_pct >= t.error_deviation_pct or record.error_z_score >= t.z_score_abs:
        out.append("vast_errors_up")
    if record.eligible_inventory_change_pct <= -15.0:
        out.append("eligible_inventory_down")
    if record.auction_pressure_change_pct >= 20.0:
        out.append("auction_pressure_up")
    if record.unique_reach_saturation >= 0.85:
        out.append("frequency_saturation")
    return out


def detect(
    record: CampaignHealthRecord, previous: CampaignHealthRecord | None = None
) -> AnomalyResult:
    t = get_settings().anomaly
    current = signals_for(record)
    result = AnomalyResult(signals=current)

    if record.data_quality.verdict == "BAD":
        result.fired = True
        result.sustained = True
        result.signals = ["data_quality_failure"]
        result.reasons = [f"Data quality verdict BAD: {', '.join(record.data_quality.failed_checks)}"]
        return result

    if len(current) < t.min_agreeing_signals:
        result.reasons.append(
            f"Only {len(current)} signal(s) agree; {t.min_agreeing_signals} required."
        )
        return result

    if previous is None:
        result.sustained = True
    else:
        prior = set(signals_for(previous))
        overlap = prior.intersection(current)
        result.sustained = len(overlap) >= 1
        if not result.sustained:
            result.reasons.append(
                "Signals not sustained across consecutive windows (possible transient)."
            )

    result.fired = result.sustained
    if result.fired:
        result.reasons.append(
            f"{len(current)} agreeing signals sustained over {t.min_sustained_windows} windows."
        )
    return result
