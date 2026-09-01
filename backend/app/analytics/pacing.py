"""Pacing and delivery formulas. Pure, deterministic, unit-tested. No AI imports."""

from __future__ import annotations


def delivery_pct(actual_impressions: float, expected_impressions: float) -> float:
    """delivery_pct = actual / expected * 100 (cumulative, since flight start)."""
    if expected_impressions <= 0:
        return 0.0
    return actual_impressions / expected_impressions * 100.0


def elapsed_pct(elapsed_hours: float, flight_hours: float) -> float:
    if flight_hours <= 0:
        return 0.0
    return min(100.0, max(0.0, elapsed_hours / flight_hours * 100.0))


def expected_impressions(goal_impressions: float, elapsed_pct_value: float) -> float:
    return goal_impressions * elapsed_pct_value / 100.0


def pacing_pct(actual_window: float, expected_window: float) -> float:
    """Current *rate* pacing over a short window, seasonality-adjusted.

    This is the early-warning signal. Cumulative delivery still looks fine for hours
    after a problem starts -- which is exactly why humans miss it.
    """
    if expected_window <= 0:
        return 0.0
    return actual_window / expected_window * 100.0


def pacing_gap_pts(pacing_pct_value: float) -> float:
    return pacing_pct_value - 100.0


def projected_end_of_flight_gap(
    required_rate_per_hour: float, pacing_pct_value: float, remaining_hours: float
) -> float:
    """Impressions we will miss by flight end if the current rate holds."""
    shortfall_factor = max(0.0, 1.0 - pacing_pct_value / 100.0)
    return max(0.0, required_rate_per_hour * shortfall_factor * remaining_hours)
