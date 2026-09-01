"""Normalization: many sources -> one CampaignHealthRecord.

Everything downstream (anomaly, evidence, diagnosis, risk, UI) consumes only this
structure, so swapping a mock adapter for a live GAM/SpringServe client changes nothing
below this line.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from ..analytics import baseline as bl
from ..analytics import errors as err_mod
from ..analytics import fill_rate as fill_mod
from ..analytics import health_score, pacing
from ..config import get_settings
from ..models import CampaignHealthRecord
from ..quality.data_quality import evaluate as evaluate_dq
from ..store.world import World

VAST_CODES = ["VAST_303", "VAST_403", "VAST_101", "VAST_402", "VAST_405"]


def _window(arr: np.ndarray, end_idx: int, hours: int) -> np.ndarray:
    lo = max(0, end_idx - hours + 1)
    return arr[lo : end_idx + 1]


def _daily_means(
    arr: np.ndarray, end_idx: int, days: int, min_idx: int = 0, offset_hours: int = 24
) -> list[float]:
    out: list[float] = []
    for d in range(days):
        hi = end_idx - offset_hours - d * 24
        lo = hi - 23
        if lo < max(0, min_idx):
            break
        seg = arr[lo : hi + 1]
        if seg.size and float(seg.sum()) > 0:
            out.append(float(seg.mean()))
    return out


def _daily_ratio(
    num: np.ndarray, den: np.ndarray, end_idx: int, days: int, min_idx: int = 0
) -> list[float]:
    out: list[float] = []
    for d in range(days):
        hi = end_idx - 24 - d * 24
        lo = hi - 23
        if lo < max(0, min_idx):
            break
        n, dd = float(num[lo : hi + 1].sum()), float(den[lo : hi + 1].sum())
        if dd > 0:
            out.append(n / dd * 100.0)
    return out


def build_record(world: World, campaign_id: str, at: datetime) -> CampaignHealthRecord:
    cfg = get_settings()
    c = world.campaigns[campaign_id]
    s = world.series[campaign_id]
    n = world.idx_for(at)
    w = cfg.current_window_hours

    flight_hours = max(1, s.end_idx - s.start_idx)
    elapsed_hours = max(0, min(flight_hours, n - s.start_idx))
    elapsed = pacing.elapsed_pct(elapsed_hours, flight_hours)
    expected_cum = pacing.expected_impressions(c.goal_impressions, elapsed)
    actual_cum = float(s.impressions[s.start_idx : n + 1].sum())
    remaining_hours = max(0, flight_hours - elapsed_hours)

    win_imps = _window(s.impressions, n, w)
    win_req = _window(s.requests, n, w)
    win_resp = _window(s.responses, n, w)
    win_err = _window(s.errors, n, w)
    win_rev = _window(s.revenue, n, w)
    win_valid = _window(s.valid, n, w)
    win_inv = _window(s.eligible_inventory, n, w)
    win_press = _window(s.auction_pressure, n, w)
    win_shape = _window(world.shape, n, w)

    # Seasonality-adjusted: a 03:00 window must not look like underdelivery.
    shape_sum = float(win_shape.sum()) or 1.0
    shape_mean = float(win_shape.mean()) or 1.0
    expected_window = s.required_rate * shape_sum
    pacing_value = pacing.pacing_pct(float(win_imps.sum()), expected_window)
    gap_pts = pacing.pacing_gap_pts(pacing_value)

    current_fill = fill_mod.fill_rate(float(win_resp.sum()), float(win_req.sum()))
    current_err = err_mod.error_rate(float(win_err.sum()), float(win_req.sum()))

    fill_hist = _daily_ratio(s.responses, s.requests, n, cfg.baseline_window_days, s.start_idx)
    err_hist = _daily_ratio(s.errors, s.requests, n, cfg.baseline_window_days, s.start_idx)
    inv_hist = _daily_means(s.eligible_inventory, n, cfg.baseline_window_days, s.start_idx)
    press_hist = _daily_means(s.auction_pressure, n, cfg.baseline_window_days, s.start_idx)

    base_fill = bl.rolling_mean(fill_hist) if fill_hist else current_fill
    base_err = bl.rolling_mean(err_hist) if err_hist else current_err
    fill_dev = bl.deviation_pct(current_fill, base_fill)
    err_dev = bl.deviation_pct(current_err, base_err)
    fill_z = bl.z_score(current_fill, base_fill, bl.rolling_std(fill_hist))
    err_z = bl.z_score(current_err, base_err, bl.rolling_std(err_hist))

    inv_now = float(win_inv.mean()) / shape_mean if win_inv.size else 0.0
    inv_change = bl.deviation_pct(inv_now, bl.rolling_mean(inv_hist)) if inv_hist else 0.0
    press_now = float(win_press.mean()) if win_press.size else 1.0
    press_change = bl.deviation_pct(press_now, bl.rolling_mean(press_hist)) if press_hist else 0.0

    last_valid_ts = None
    for i in range(n, max(-1, n - 48), -1):
        if s.valid[i] and s.requests[i] > 0:
            last_valid_ts = world.ts_for(i)
            break

    dq = evaluate_dq(
        campaign_id=campaign_id,
        ts=at,
        window_impressions=win_imps,
        window_requests=win_req,
        window_valid=win_valid,
        window_revenue=win_rev,
        expected_impressions=expected_cum,
        last_valid_ts=last_valid_ts,
    )

    score, band, components = health_score.compute(
        pacing_gap=gap_pts,
        pacing_pct=pacing_value,
        fill_deviation_pct=fill_dev,
        error_deviation_pct=err_dev,
        eligible_inventory_change_pct=inv_change,
        dq_score=dq.score,
    )

    targeting_recent = bool(
        c.targeting.last_changed_at
        and (at - c.targeting.last_changed_at) <= timedelta(hours=72)
    )

    total_errors = int(win_err.sum())
    breakdown = _vast_breakdown(total_errors, s.worst_vast_code, dominant=s.cause == "VAST_PLAYBACK_ERRORS" or campaign_id == world.golden_id)

    return CampaignHealthRecord(
        campaign_id=campaign_id,
        line_item_id=c.line_item_id,
        campaign_name=c.name,
        advertiser=c.advertiser,
        campaign_type=c.campaign_type,
        ts=at,
        expected_impressions=int(expected_cum),
        actual_impressions=int(actual_cum),
        delivery_pct=round(pacing.delivery_pct(actual_cum, expected_cum), 2),
        elapsed_pct=round(elapsed, 2),
        pacing_pct=round(pacing_value, 2),
        pacing_gap_pts=round(gap_pts, 2),
        fill_rate=round(current_fill, 2),
        baseline_fill_rate=round(base_fill, 2),
        fill_deviation_pct=round(fill_dev, 2),
        fill_z_score=round(fill_z, 2),
        error_rate=round(current_err, 3),
        baseline_error_rate=round(base_err, 3),
        error_deviation_pct=round(err_dev, 2),
        error_z_score=round(err_z, 2),
        expected_revenue=round(expected_cum / 1000 * c.ecpm, 2),
        actual_revenue=round(float(s.revenue[s.start_idx : n + 1].sum()), 2),
        ecpm=c.ecpm,
        eligible_inventory_change_pct=round(inv_change, 2),
        auction_pressure_change_pct=round(press_change, 2),
        targeting_changed_recently=targeting_recent,
        creative_error_share=round(s.creative_error_share, 3),
        unique_reach_saturation=round(s.reach_saturation, 3),
        worst_platform=s.worst_platform,
        worst_vast_code=s.worst_vast_code,
        vast_error_breakdown=breakdown,
        health_score=score,
        health_band=band,
        score_components=components,
        data_quality=dq,
    )


def _vast_breakdown(total: int, worst: str | None, dominant: bool) -> dict[str, int]:
    if total <= 0:
        return {}
    codes = VAST_CODES if not worst else [worst] + [c for c in VAST_CODES if c != worst]
    shares = [0.68, 0.14, 0.08, 0.06, 0.04] if dominant else [0.32, 0.24, 0.20, 0.14, 0.10]
    return {code: int(total * share) for code, share in zip(codes, shares)}


def remaining_hours(world: World, campaign_id: str, at: datetime) -> int:
    s = world.series[campaign_id]
    return max(0, s.end_idx - world.idx_for(at))


def flight_hours(world: World, campaign_id: str) -> int:
    s = world.series[campaign_id]
    return max(1, s.end_idx - s.start_idx)
