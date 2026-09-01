"""The seven scenarios that must hold, plus the grounding gate."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.ai import grounding
from app.analytics import anomaly, health_score, pacing, prioritization, revenue_risk
from app.diagnosis import cause_scoring, evidence_builder, root_cause_rules
from app.store.memory import store


@pytest.fixture(scope="module")
def guardian():
    store.reset()
    store.run_analysis()
    return store


def _record(guardian, campaign_id):
    return guardian.record(campaign_id)


def _causes(guardian, campaign_id):
    record = _record(guardian, campaign_id)
    package = evidence_builder.build(record, guardian.campaign(campaign_id))
    hits = root_cause_rules.evaluate(record, package)
    return {c.cause for c in cause_scoring.rank(hits)}, record, package


# 1 --------------------------------------------------------------------------------

def test_healthy_campaign_raises_no_incident(guardian):
    healthy = [
        r for r in guardian.all_records()
        if r.health_band == "HEALTHY" and r.data_quality.verdict == "OK"
    ]
    assert healthy, "expected healthy campaigns in the seeded world"
    for record in healthy[:25]:
        previous = guardian.record(record.campaign_id, guardian.now() - timedelta(hours=1))
        assert not anomaly.detect(record, previous).fired


# 2 --------------------------------------------------------------------------------

def test_underdelivery_creates_critical_incident_with_risk(guardian):
    incident = guardian._open_incident_for(guardian.world.golden_id)
    assert incident is not None
    assert incident.severity == "CRITICAL"
    assert incident.priority == "P0"
    assert incident.revenue_risk.expected > 0
    assert "pacing_down" in incident.signals


# 3 --------------------------------------------------------------------------------

def test_fill_rate_collapse_yields_supply_candidate(guardian):
    causes, record, _ = _causes(guardian, guardian.world.golden_id)
    assert record.fill_deviation_pct <= -20
    assert "SUPPLY_SHORTAGE" in causes


# 4 --------------------------------------------------------------------------------

def test_vast_spike_yields_playback_candidate(guardian):
    causes, record, _ = _causes(guardian, guardian.world.golden_id)
    assert record.error_rate >= 2 * record.baseline_error_rate
    assert "VAST_PLAYBACK_ERRORS" in causes


# 5 --------------------------------------------------------------------------------

def test_multi_signal_cascade_is_ranked_with_targeting_first(guardian):
    record = _record(guardian, guardian.world.golden_id)
    package = evidence_builder.build(record, guardian.campaign(guardian.world.golden_id))
    ranked = cause_scoring.rank(root_cause_rules.evaluate(record, package))
    assert len(ranked) >= 3
    assert ranked[0].cause == "TARGETING_RESTRICTION"
    assert ranked[0].confidence >= ranked[1].confidence
    assert abs(sum(c.confidence for c in ranked) - 1.0) < 1e-6
    assert all(c.evidence_ids for c in ranked), "a rule may not fire without evidence"


# 6 --------------------------------------------------------------------------------

def test_revenue_risk_maths_is_exact():
    risk = revenue_risk.compute(realized_gap=0.0, projected_gap=1_900_000, ecpm=12.0)
    assert risk.expected == 22_800.00
    assert risk.conservative == pytest.approx(14_820.0)
    assert risk.worst_case == pytest.approx(30_780.0)
    assert risk.impression_gap == 1_900_000


# 7 --------------------------------------------------------------------------------

def test_broken_feed_is_a_data_quality_incident_not_underdelivery(guardian):
    assert guardian.world.dq_campaign_ids
    for campaign_id in guardian.world.dq_campaign_ids:
        record = guardian.record(campaign_id)
        assert record.data_quality.verdict == "BAD"
        previous = guardian.record(campaign_id, guardian.now() - timedelta(hours=1))
        result = anomaly.detect(record, previous)
        assert result.fired
        assert result.signals == ["data_quality_failure"]
        incident = guardian._open_incident_for(campaign_id)
        assert incident is not None and incident.is_data_quality


# grounding -------------------------------------------------------------------------

def test_grounding_rejects_a_fabricated_number(guardian):
    record = _record(guardian, guardian.world.golden_id)
    package = evidence_builder.build(record, guardian.campaign(guardian.world.golden_id))

    honest = f"Fill rate is {record.fill_rate:.1f}% against baseline [EV-03]."
    assert grounding.validate(honest, package).passed

    fabricated = "Fill rate collapsed to 17.3% after a 62.9% inventory loss [EV-03]."
    result = grounding.validate(fabricated, package)
    assert not result.passed
    assert any("17.3" in v for v in result.violations)

    bad_citation = f"Pacing is {record.pacing_pct:.1f}% of plan [EV-99]."
    assert not grounding.validate(bad_citation, package).passed


def test_diagnosis_is_grounded_and_cites_evidence(guardian):
    incident = guardian._open_incident_for(guardian.world.golden_id)
    diagnosed = guardian.diagnose(incident.incident_id)
    d = diagnosed.diagnosis
    assert d is not None and d.grounding_passed
    assert d.evidence_used
    valid = {i.id for i in guardian.evidence[incident.incident_id].items}
    assert set(d.evidence_used).issubset(valid)
    assert diagnosed.recommendation is not None
    assert diagnosed.recommendation.requires_approval


# formulas --------------------------------------------------------------------------

def test_pacing_and_health_formulas():
    assert pacing.delivery_pct(3_100_000, 5_000_000) == pytest.approx(62.0)
    assert pacing.pacing_gap_pts(62.0) == pytest.approx(-38.0)
    assert pacing.projected_end_of_flight_gap(41_667, 62.0, 120) == pytest.approx(
        41_667 * 0.38 * 120
    )
    score, band, components = health_score.compute(
        pacing_gap=0.0, pacing_pct=100.0, fill_deviation_pct=0.0,
        error_deviation_pct=0.0, eligible_inventory_change_pct=0.0, dq_score=1.0,
    )
    assert score == 100.0 and band == "HEALTHY"
    assert sum(c.weight for c in components) == pytest.approx(100.0)

    worst, band2, _ = health_score.compute(
        pacing_gap=-90.0, pacing_pct=10.0, fill_deviation_pct=-60.0,
        error_deviation_pct=500.0, eligible_inventory_change_pct=-60.0, dq_score=0.0,
    )
    assert worst == 0.0 and band2 == "CRITICAL"


def test_prioritization_is_monotonic_in_money():
    low = prioritization.risk_score(
        expected_risk=1_000, severity="HIGH", confidence=0.9, urgency_value=0.5
    )
    high = prioritization.risk_score(
        expected_risk=25_000, severity="HIGH", confidence=0.9, urgency_value=0.5
    )
    assert high > low
    assert prioritization.priority_for(high) <= prioritization.priority_for(low)


def test_analytics_layer_never_imports_the_ai_layer():
    """The deterministic engine must stay independent of the LLM."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "analytics"
    for path in root.glob("*.py"):
        source = path.read_text()
        assert "app.ai" not in source and "from ..ai" not in source, path.name
