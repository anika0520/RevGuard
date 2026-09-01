"""Weighted campaign health score. Weights are configurable business rules (config.py),
not magic numbers -- and every component is returned so the UI can show the breakdown.
"""

from __future__ import annotations

from ..config import get_settings
from ..models import HealthBand, ScoreComponent


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def pacing_penalty(pacing_gap: float, pacing_pct: float) -> float:
    if pacing_pct > 130.0:
        return _clamp((pacing_pct - 130.0) / 40.0)
    return _clamp(-pacing_gap / 60.0)


def fill_penalty(fill_deviation_pct: float) -> float:
    return _clamp(-fill_deviation_pct / 40.0)


def error_penalty(error_deviation_pct: float) -> float:
    return _clamp(error_deviation_pct / 300.0)


def supply_penalty(eligible_inventory_change_pct: float) -> float:
    return _clamp(-eligible_inventory_change_pct / 40.0)


def data_quality_penalty(dq_score: float) -> float:
    return _clamp(1.0 - dq_score)


def compute(
    *,
    pacing_gap: float,
    pacing_pct: float,
    fill_deviation_pct: float,
    error_deviation_pct: float,
    eligible_inventory_change_pct: float,
    dq_score: float,
) -> tuple[float, HealthBand, list[ScoreComponent]]:
    w = get_settings().health_weights
    parts = [
        ("Pacing", w.pacing, pacing_penalty(pacing_gap, pacing_pct)),
        ("Fill rate", w.fill_rate, fill_penalty(fill_deviation_pct)),
        ("Error rate", w.error_rate, error_penalty(error_deviation_pct)),
        ("Supply signal", w.supply_signal, supply_penalty(eligible_inventory_change_pct)),
        ("Data quality", w.data_quality, data_quality_penalty(dq_score)),
    ]
    components = [
        ScoreComponent(label=label, weight=weight, penalty=round(pen, 4),
                       points_lost=round(weight * pen, 2))
        for label, weight, pen in parts
    ]
    score = round(max(0.0, 100.0 - sum(c.points_lost for c in components)), 1)
    return score, band_for(score), components


def band_for(score: float) -> HealthBand:
    b = get_settings().health_bands
    if score <= b.critical_max:
        return "CRITICAL"
    if score <= b.high_risk_max:
        return "HIGH_RISK"
    if score <= b.warning_max:
        return "WARNING"
    return "HEALTHY"
