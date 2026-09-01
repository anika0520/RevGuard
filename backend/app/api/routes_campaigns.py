"""Campaign endpoints."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Query

from ..ingestion import normalizer
from ..store.memory import store
from .common import ok

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

SORT_KEYS = {
    "risk": lambda r: -r["revenue_at_risk"],
    "health": lambda r: r["health_score"],
    "pacing": lambda r: r["pacing_pct"],
    "fill": lambda r: r["fill_rate"],
    "errors": lambda r: -r["error_rate"],
    "name": lambda r: r["campaign_name"],
}


def _row(record) -> dict:
    campaign = store.campaign(record.campaign_id)
    risk, _, remaining = store.risk_for(record)
    return {
        "campaign_id": record.campaign_id,
        "campaign_name": record.campaign_name,
        "advertiser": record.advertiser,
        "campaign_type": record.campaign_type,
        "health_score": record.health_score,
        "health_band": record.health_band,
        "pacing_pct": record.pacing_pct,
        "delivery_pct": record.delivery_pct,
        "fill_rate": record.fill_rate,
        "baseline_fill_rate": record.baseline_fill_rate,
        "error_rate": record.error_rate,
        "baseline_error_rate": record.baseline_error_rate,
        "expected_impressions": record.expected_impressions,
        "actual_impressions": record.actual_impressions,
        "revenue_at_risk": risk.expected,
        "goal_impressions": campaign.goal_impressions,
        "ecpm": record.ecpm,
        "geos": campaign.targeting.geos,
        "platforms": campaign.targeting.platforms,
        "end_date": campaign.end_date.isoformat(),
        "remaining_hours": remaining,
        "data_quality": record.data_quality.verdict,
    }


@router.get("")
def list_campaigns(
    q: str | None = None,
    band: str | None = None,
    campaign_type: str | None = None,
    geo: str | None = None,
    platform: str | None = None,
    sort: str = "risk",
    limit: int = Query(250, le=500),
    offset: int = 0,
):
    rows = [_row(r) for r in store.all_records()]
    if q:
        needle = q.lower()
        rows = [
            r for r in rows
            if needle in r["campaign_name"].lower()
            or needle in r["advertiser"].lower()
            or needle in r["campaign_id"].lower()
        ]
    if band:
        wanted = {b.strip().upper() for b in band.split(",")}
        rows = [r for r in rows if r["health_band"] in wanted]
    if campaign_type:
        rows = [r for r in rows if r["campaign_type"] == campaign_type]
    if geo:
        rows = [r for r in rows if geo in r["geos"]]
    if platform:
        rows = [r for r in rows if platform in r["platforms"]]

    rows.sort(key=SORT_KEYS.get(sort, SORT_KEYS["risk"]))
    total = len(rows)
    return ok(rows[offset : offset + limit], total=total, offset=offset, limit=limit)


@router.get("/{campaign_id}")
def get_campaign(campaign_id: str):
    if campaign_id not in store.world.campaigns:
        raise HTTPException(404, "Campaign not found")
    record = store.record(campaign_id)
    campaign = store.campaign(campaign_id)
    risk, projected, remaining = store.risk_for(record)
    incident = store._open_incident_for(campaign_id)
    return ok(
        {
            "campaign": campaign.model_dump(mode="json"),
            "health": record.model_dump(mode="json"),
            "revenue_risk": risk.model_dump(mode="json"),
            "projected_gap": int(projected),
            "remaining_hours": remaining,
            "flight_hours": normalizer.flight_hours(store.world, campaign_id),
            "incident_id": incident.incident_id if incident else None,
            "supply_tags": [t.model_dump(mode="json") for t in store.world.tags[campaign_id]],
        }
    )


@router.get("/{campaign_id}/timeseries")
def timeseries(campaign_id: str, hours: int = Query(48, ge=6, le=336)):
    if campaign_id not in store.world.campaigns:
        raise HTTPException(404, "Campaign not found")
    world, s = store.world, store.world.series[campaign_id]
    n = world.idx_for(store.now())
    lo = max(s.start_idx, n - hours + 1)
    points = []
    cumulative = float(s.impressions[s.start_idx : lo].sum())
    cumulative_expected = s.required_rate * max(0, lo - s.start_idx)
    for i in range(lo, n + 1):
        cumulative += float(s.impressions[i])
        cumulative_expected += s.required_rate
        expected_hour = s.required_rate * float(world.shape[i])
        points.append(
            {
                "ts": world.ts_for(i).isoformat(),
                "impressions": int(s.impressions[i]),
                "expected_impressions": int(expected_hour),
                "cumulative_impressions": int(cumulative),
                "cumulative_expected": int(cumulative_expected),
                "fill_rate": round(
                    float(s.responses[i]) / float(s.requests[i]) * 100 if s.requests[i] else 0.0, 2
                ),
                "error_rate": round(
                    float(s.errors[i]) / float(s.requests[i]) * 100 if s.requests[i] else 0.0, 2
                ),
                "eligible_inventory": int(s.eligible_inventory[i]),
                "revenue": round(float(s.revenue[i]), 2),
                "valid": bool(s.valid[i]),
            }
        )
    onset = world.ts_for(s.onset_idx).isoformat() if s.onset_idx is not None else None
    remediated = (
        world.ts_for(s.remediated_at_idx).isoformat() if s.remediated_at_idx is not None else None
    )
    return ok(
        points,
        onset_at=onset,
        remediated_at=remediated,
        baseline_fill_rate=round(s.baseline_fill * 100, 2),
        baseline_error_rate=round(s.baseline_error * 100, 2),
    )


@router.get("/{campaign_id}/health")
def health(campaign_id: str):
    if campaign_id not in store.world.campaigns:
        raise HTTPException(404, "Campaign not found")
    record = store.record(campaign_id)
    previous = store.record(campaign_id, store.now() - timedelta(hours=1))
    from ..analytics import anomaly

    result = anomaly.detect(record, previous)
    return ok(
        {
            "record": record.model_dump(mode="json"),
            "anomaly": {
                "signals": result.signals,
                "sustained": result.sustained,
                "fired": result.fired,
                "reasons": result.reasons,
            },
        }
    )
