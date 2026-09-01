"""Turn many incidents into a ranked queue. Ad Ops gets 'do these 3 first', not 50 alerts."""

from __future__ import annotations

from ..models import Priority, Severity

SEVERITY_WEIGHT = {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.45, "LOW": 0.2}


def severity_for(health_score: float, is_data_quality: bool = False) -> Severity:
    if is_data_quality:
        return "HIGH"
    if health_score <= 30:
        return "CRITICAL"
    if health_score <= 50:
        return "HIGH"
    if health_score <= 70:
        return "MEDIUM"
    return "LOW"


def urgency(remaining_hours: float, flight_hours: float) -> float:
    """Less time left to recover => more urgent."""
    if flight_hours <= 0:
        return 1.0
    return max(0.15, min(1.0, 1.0 - (remaining_hours / flight_hours) * 0.7))


def risk_score(
    *, expected_risk: float, severity: Severity, confidence: float, urgency_value: float,
    max_risk_reference: float = 30_000.0,
) -> float:
    """risk_score = normalized($ impact) x severity x confidence x urgency."""
    normalized = min(1.0, expected_risk / max_risk_reference)
    return round(normalized * SEVERITY_WEIGHT[severity] * confidence * urgency_value, 4)


def priority_for(score: float) -> Priority:
    if score >= 0.30:
        return "P0"
    if score >= 0.16:
        return "P1"
    if score >= 0.06:
        return "P2"
    return "P3"
