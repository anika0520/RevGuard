"""Data-quality gate. Runs BEFORE analytics.

If the feed is broken we raise a DATA_QUALITY incident -- we never report a campaign
as underdelivering when the truth is the data did not land.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from ..config import get_settings
from ..models import DataQualityCheck, DataQualityReport


def evaluate(
    *,
    campaign_id: str,
    ts: datetime,
    window_impressions: np.ndarray,
    window_requests: np.ndarray,
    window_valid: np.ndarray,
    window_revenue: np.ndarray,
    expected_impressions: float,
    last_valid_ts: datetime | None,
) -> DataQualityReport:
    cfg = get_settings()
    checks: list[DataQualityCheck] = []

    checks.append(DataQualityCheck(name="campaign_id_present", passed=bool(campaign_id)))
    checks.append(DataQualityCheck(name="timestamp_valid", passed=ts.year > 2000))

    numeric_ok = bool(np.all(np.isfinite(window_impressions)) and np.all(window_impressions >= 0))
    checks.append(DataQualityCheck(name="impressions_numeric_non_negative", passed=numeric_ok))

    checks.append(
        DataQualityCheck(name="expected_impressions_gt_zero", passed=expected_impressions > 0)
    )

    revenue_ok = bool(np.all(np.isfinite(window_revenue)))
    checks.append(DataQualityCheck(name="revenue_valid", passed=revenue_ok))

    missing = int((~window_valid).sum())
    checks.append(
        DataQualityCheck(
            name="no_missing_hours_in_window",
            passed=missing == 0,
            detail=f"{missing} missing hour(s) in the {window_valid.size}h window",
        )
    )

    stale_minutes = (
        (ts - last_valid_ts).total_seconds() / 60 if last_valid_ts else 10_000.0
    )
    fresh = stale_minutes <= cfg.data_freshness_sla_minutes
    checks.append(
        DataQualityCheck(
            name="freshness_within_sla",
            passed=fresh,
            detail=f"Last valid record {int(stale_minutes)} min old (SLA {cfg.data_freshness_sla_minutes} min)",
        )
    )

    zero_run = _longest_zero_run(window_requests)
    checks.append(
        DataQualityCheck(
            name="no_prolonged_zero_request_run",
            passed=zero_run < 4,
            detail=f"{zero_run} consecutive hours with zero requests",
        )
    )

    passed = sum(1 for c in checks if c.passed)
    score = round(passed / len(checks), 3)
    verdict = "OK" if score >= 0.95 else ("DEGRADED" if score >= 0.8 else "BAD")
    return DataQualityReport(score=score, verdict=verdict, checks=checks)


def _longest_zero_run(values: np.ndarray) -> int:
    best = run = 0
    for v in values:
        run = run + 1 if v <= 0 else 0
        best = max(best, run)
    return best
