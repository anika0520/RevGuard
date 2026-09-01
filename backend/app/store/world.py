"""Deterministic mock universe. Same seed -> same demo, every single time.

The world is a set of hourly numpy series per campaign spanning `origin .. origin+hours`.
The "current view" is a slice at the simulation clock, so advancing time re-derives
everything naturally -- including a scripted degradation cascade and, after a human
approves a fix, the recovery back toward the nominal (undegraded) series.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from ..config import get_settings, sim_start, world_origin
from ..models import Campaign, SupplyTag, Targeting

ADVERTISERS = [
    "Acme", "Nike", "Disney", "Sony", "Samsung", "Adidas", "Toyota", "HSBC", "Pepsi",
    "Netflix", "Unilever", "L'Oreal", "Ford", "Barclays", "Vodafone", "Heineken",
    "Sky", "BMW", "Spotify", "Lego", "Booking", "Kelloggs", "Visa", "Airbnb",
    "Mastercard", "Nestle", "Puma", "Dyson", "Uber", "Deliveroo",
]
TYPES = ["CTV", "Sports", "Entertainment", "News", "Kids", "Movies", "Gaming"]
GEOS = ["UK", "US", "Canada", "Germany", "Australia"]
PLATFORMS = ["Roku", "Samsung TV", "LG", "Fire TV", "Web", "Mobile"]
DEVICES = ["CTV", "Desktop", "Mobile", "Tablet"]
FLIGHT_LABELS = ["Q3", "Always On", "Launch", "Brand", "Retargeting", "Upper Funnel"]
ECPM_BY_TYPE = {
    "CTV": (18.0, 24.0), "Sports": (12.0, 16.0), "Movies": (10.0, 15.0),
    "Entertainment": (8.0, 12.0), "Kids": (7.0, 11.0), "Gaming": (5.0, 9.0),
    "News": (6.0, 9.0),
}
VAST_CODES = ["VAST_303", "VAST_403", "VAST_101", "VAST_402", "VAST_405"]

# Instantaneous delivery-rate factor once a degradation is fully ramped in.
PROFILE_SPEC = {
    "CRITICAL": (0.20, 0.36),
    "HIGH_RISK": (0.45, 0.62),
    "WARNING": (0.70, 0.86),
    "HEALTHY": (0.97, 1.03),
}
CAUSE_POOL = [
    "TARGETING_RESTRICTION", "SUPPLY_SHORTAGE", "VAST_PLAYBACK_ERRORS",
    "GAM_COMPETITION", "FREQUENCY_CAP", "CREATIVE_ISSUE",
]

# cause -> (fill slope, error slope, eligible-inventory slope, auction-pressure slope)
CAUSE_EFFECT = {
    "TARGETING_RESTRICTION": (-0.29, 3.14, -0.31, 0.0),
    "SUPPLY_SHORTAGE": (-0.38, 0.35, -0.28, 0.0),
    "VAST_PLAYBACK_ERRORS": (-0.08, 4.20, 0.0, 0.0),
    "GAM_COMPETITION": (-0.26, 0.0, -0.05, 0.34),
    "FREQUENCY_CAP": (-0.06, 0.0, -0.19, 0.0),
    "CREATIVE_ISSUE": (-0.04, 2.60, 0.0, 0.0),
}


@dataclass
class CampaignSeries:
    requests: np.ndarray
    responses: np.ndarray
    errors: np.ndarray
    impressions: np.ndarray
    revenue: np.ndarray
    eligible_inventory: np.ndarray
    auction_pressure: np.ndarray
    valid: np.ndarray
    # Undegraded counterfactual -- what the campaign would have done if healthy.
    nominal_requests: np.ndarray
    nominal_responses: np.ndarray
    nominal_errors: np.ndarray
    nominal_impressions: np.ndarray
    nominal_revenue: np.ndarray
    nominal_inventory: np.ndarray
    start_idx: int
    end_idx: int          # logical; may exceed the generated array length
    fill_end: int         # last generated index
    required_rate: float
    baseline_fill: float
    baseline_error: float
    cause: str | None = None
    onset_idx: int | None = None
    worst_platform: str | None = None
    worst_vast_code: str | None = None
    creative_error_share: float = 0.05
    reach_saturation: float = 0.35
    remediated_at_idx: int | None = None


@dataclass
class World:
    origin: datetime
    hours: int
    sim_start: datetime
    shape: np.ndarray = field(default_factory=lambda: np.ones(1))
    campaigns: dict[str, Campaign] = field(default_factory=dict)
    series: dict[str, CampaignSeries] = field(default_factory=dict)
    tags: dict[str, list[SupplyTag]] = field(default_factory=dict)
    profiles: dict[str, str] = field(default_factory=dict)
    dq_campaign_ids: list[str] = field(default_factory=list)
    recovered_campaign_ids: list[str] = field(default_factory=list)
    overdelivering_campaign_id: str = ""
    golden_id: str = "ACME-CTV-123"

    def idx_for(self, ts: datetime) -> int:
        return max(0, min(self.hours - 1, int((ts - self.origin).total_seconds() // 3600)))

    def ts_for(self, idx: int) -> datetime:
        return self.origin + timedelta(hours=idx)

    def apply_remediation(self, campaign_id: str, at: datetime, recovery: float = 0.94) -> None:
        """Blend the future back toward the nominal series so risk visibly burns down."""
        s = self.series.get(campaign_id)
        if s is None:
            return
        i0 = self.idx_for(at)
        s.remediated_at_idx = i0
        end = min(self.hours, s.fill_end + 1)
        if i0 >= end:
            return
        span = np.arange(i0, end)
        blend = np.clip((span - i0) / 4.0, 0.0, 1.0) * recovery
        pairs = (
            (s.requests, s.nominal_requests),
            (s.responses, s.nominal_responses),
            (s.errors, s.nominal_errors),
            (s.impressions, s.nominal_impressions),
            (s.revenue, s.nominal_revenue),
            (s.eligible_inventory, s.nominal_inventory),
        )
        for cur, nom in pairs:
            cur[i0:end] = cur[i0:end] * (1 - blend) + nom[i0:end] * blend
        s.auction_pressure[i0:end] = s.auction_pressure[i0:end] * (1 - blend) + blend


def _diurnal_curve() -> np.ndarray:
    raw = np.array(
        [max(0.3, 1.0 + 1.2 * math.sin((h - 5) / 24 * 2 * math.pi) ** 3) for h in range(24)]
    )
    return raw / raw.mean()


DIURNAL = _diurnal_curve()


def _shape_array(origin: datetime, hours: int) -> np.ndarray:
    stamps = [origin + timedelta(hours=h) for h in range(hours)]
    return np.array([DIURNAL[t.hour] * (0.88 if t.weekday() >= 5 else 1.045) for t in stamps])


def _emit(target, fill, errate, inv_mult, ecpm, span, out) -> None:
    req, resp, err, imps, rev, inv = out
    r = target / np.maximum(0.05, fill * (1 - errate))
    req[span] = r
    resp[span] = r * fill
    err[span] = r * errate
    imps[span] = np.maximum(0.0, r * fill - r * errate)
    rev[span] = imps[span] / 1000 * ecpm
    inv[span] = r * 1.65 * inv_mult


def build_world() -> World:
    cfg = get_settings()
    origin, start = world_origin(), sim_start()
    hours = cfg.history_days * 24 + cfg.future_hours
    world = World(origin=origin, hours=hours, sim_start=start)
    shape_all = _shape_array(origin, hours)
    world.shape = shape_all
    now_idx = world.idx_for(start)

    profiles = (
        ["CRITICAL"] * 7 + ["HIGH_RISK"] * 15 + ["WARNING"] * 32
        + ["HEALTHY"] * (cfg.campaign_count - 54)
    )
    rng_global = np.random.default_rng(cfg.random_seed)
    profiles = [profiles[i] for i in rng_global.permutation(len(profiles))]
    profiles[0] = "CRITICAL"  # slot 0 is the golden incident

    for i in range(cfg.campaign_count):
        rng = np.random.default_rng(cfg.random_seed * 1000 + i)
        golden = i == 0
        profile = profiles[i]

        if golden:
            cid, name, adv, ctype = world.golden_id, "Acme Sports CTV", "Acme", "Sports"
            goal, ecpm, flight_days, elapsed_days = 10_000_000, 12.0, 10, 5
            geos, plats, cats, devices = ["UK"], ["Roku", "Samsung TV"], ["Sports"], ["CTV"]
            cause, rate_factor, onset_h = "TARGETING_RESTRICTION", 0.70, 6
            priority = 8
        else:
            adv = ADVERTISERS[int(rng.integers(0, len(ADVERTISERS)))]
            ctype = TYPES[int(rng.integers(0, len(TYPES)))]
            cid = f"{adv[:4].upper()}-{ctype[:3].upper()}-{100 + i}"
            name = f"{adv} {ctype} {FLIGHT_LABELS[i % len(FLIGHT_LABELS)]}"
            lo, hi = ECPM_BY_TYPE[ctype]
            ecpm = round(float(rng.uniform(lo, hi)), 2)
            goal = int(rng.integers(1, 21)) * 1_000_000
            flight_days = int(rng.integers(7, 31))
            elapsed_days = int(rng.integers(2, max(3, flight_days - 1)))
            geos = [str(g) for g in rng.choice(GEOS, size=int(rng.integers(1, 3)), replace=False)]
            plats = [str(p) for p in rng.choice(PLATFORMS, size=int(rng.integers(1, 4)), replace=False)]
            devices = [str(d) for d in rng.choice(DEVICES, size=int(rng.integers(1, 3)), replace=False)]
            cats = [ctype]
            priority = int(rng.integers(4, 13))
            if profile == "HEALTHY":
                cause, rate_factor, onset_h = None, 1.0, 0
            else:
                cause = CAUSE_POOL[int(rng.integers(0, len(CAUSE_POOL)))]
                rate_factor = float(rng.uniform(*PROFILE_SPEC[profile]))
                onset_h = int(rng.integers(6, 30))

        start_dt = start - timedelta(days=elapsed_days)
        end_dt = start_dt + timedelta(days=flight_days)
        start_idx = world.idx_for(start_dt)
        end_idx = int((end_dt - origin).total_seconds() // 3600)
        fill_end = min(hours - 1, end_idx)
        flight_hours = max(1, end_idx - start_idx)
        required_rate = goal / flight_hours
        base_fill = 0.72 if golden else float(rng.uniform(0.62, 0.78))
        base_err = 0.021 if golden else float(rng.uniform(0.014, 0.026))
        onset_idx = (now_idx - onset_h) if cause else None

        req, resp, err, imps, rev, inv = (np.zeros(hours) for _ in range(6))
        n_req, n_resp, n_err, n_imps, n_rev, n_inv = (np.zeros(hours) for _ in range(6))
        pressure = np.ones(hours)
        valid = np.ones(hours, dtype=bool)

        span = np.arange(start_idx, fill_end + 1)
        if span.size:
            noise = np.clip(rng.normal(1.0, 0.05, span.size), 0.7, 1.3)
            nominal_target = required_rate * shape_all[span] * noise
            ramp = (
                np.clip((span - onset_idx + 1) / 2.0, 0.0, 1.0)
                if onset_idx is not None
                else np.zeros(span.size)
            )
            fs, es, ivs, ps = CAUSE_EFFECT.get(cause or "", (0.0, 0.0, 0.0, 0.0))

            _emit(
                nominal_target * (1.0 - (1.0 - rate_factor) * ramp),
                base_fill * (1.0 + fs * ramp),
                np.clip(base_err * (1.0 + es * ramp), 0.0, 0.6),
                1.0 + ivs * ramp,
                ecpm, span, (req, resp, err, imps, rev, inv),
            )
            _emit(
                nominal_target,
                np.full(span.size, base_fill),
                np.full(span.size, base_err),
                np.ones(span.size),
                ecpm, span, (n_req, n_resp, n_err, n_imps, n_rev, n_inv),
            )
            pressure[span] = 1.0 + ps * ramp

        world.campaigns[cid] = Campaign(
            campaign_id=cid,
            line_item_id=f"LI-{600000 + i}",
            name=name,
            advertiser=adv,
            campaign_type=ctype,  # type: ignore[arg-type]
            start_date=start_dt.date(),
            end_date=end_dt.date(),
            goal_impressions=goal,
            ecpm=ecpm,
            priority=priority,
            status="ACTIVE",
            targeting=Targeting(
                geos=geos, devices=devices, platforms=plats, content_categories=cats,
                frequency_cap=int(rng.integers(2, 7)),
                last_changed_at=(
                    world.ts_for(onset_idx)
                    if cause == "TARGETING_RESTRICTION" and onset_idx is not None
                    else start_dt - timedelta(days=int(rng.integers(5, 40)))
                ),
            ),
            created_at=start_dt - timedelta(days=3),
        )
        world.series[cid] = CampaignSeries(
            requests=req, responses=resp, errors=err, impressions=imps, revenue=rev,
            eligible_inventory=inv, auction_pressure=pressure, valid=valid,
            nominal_requests=n_req, nominal_responses=n_resp, nominal_errors=n_err,
            nominal_impressions=n_imps, nominal_revenue=n_rev, nominal_inventory=n_inv,
            start_idx=start_idx, end_idx=end_idx, fill_end=fill_end,
            required_rate=required_rate, baseline_fill=base_fill, baseline_error=base_err,
            cause=cause, onset_idx=onset_idx,
            worst_platform=("Roku" if golden else plats[0]),
            worst_vast_code=("VAST_303" if golden else VAST_CODES[int(rng.integers(0, 5))]),
            creative_error_share=(
                0.62 if cause == "CREATIVE_ISSUE" else float(rng.uniform(0.05, 0.3))
            ),
            reach_saturation=(
                0.91 if cause == "FREQUENCY_CAP" else float(rng.uniform(0.2, 0.6))
            ),
        )
        world.profiles[cid] = profile
        world.tags[cid] = [
            SupplyTag(
                tag_id=f"TAG-{i:03d}-{t}",
                tag_name=f"{adv} {plats[t % len(plats)]} {geos[0]} CTV",
                campaign_id=cid,
                platform=plats[t % len(plats)],
                country=geos[0],
                device=devices[0],
            )
            for t in range(int(rng.integers(3, 9)))
        ]

    _inject_special_cases(world, now_idx)
    return world


def _inject_special_cases(world: World, now_idx: int) -> None:
    """Data-quality faults, an overdelivering campaign, and self-recovered dips.

    These exist so the demo can prove precision: the system must NOT report a broken
    feed as underdelivery, must flag overdelivery too, and must not fire on transients.
    """
    cfg = get_settings()
    ids = [c for c in world.campaigns if c != world.golden_id]
    rng = np.random.default_rng(cfg.random_seed + 7)
    lo = max(0, now_idx - 5)

    for cid in [ids[i] for i in rng.choice(len(ids), size=3, replace=False)]:
        s = world.series[cid]
        s.valid[lo : now_idx + 1] = False
        for arr in (s.impressions, s.revenue, s.requests, s.responses, s.errors):
            arr[lo : now_idx + 1] = 0.0
        world.dq_campaign_ids.append(cid)

    over = ids[int(rng.integers(0, len(ids)))]
    so = world.series[over]
    hi = max(0, now_idx - 40)
    for arr in (so.impressions, so.revenue, so.requests, so.responses):
        arr[hi : now_idx + 1] *= 1.45
    world.overdelivering_campaign_id = over

    remaining = [c for c in ids if c not in world.dq_campaign_ids and c != over]
    for cid in [remaining[i] for i in rng.choice(len(remaining), size=6, replace=False)]:
        s = world.series[cid]
        a, b = max(0, now_idx - 34), max(0, now_idx - 14)
        for arr in (s.impressions, s.responses, s.revenue):
            arr[a:b] *= 0.55
        world.recovered_campaign_ids.append(cid)
