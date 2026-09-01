"""Executive metrics, impact ledger, tool registry and live business-rule settings."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Body, Query

from ..config import get_settings
from ..events.bus import bus
from ..store.memory import store
from ..tools.definitions import TOOL_DEFINITIONS
from .common import ok

router = APIRouter(prefix="/api", tags=["metrics"])

ACTIVE = ("OPEN", "INVESTIGATING", "AWAITING_APPROVAL", "ACTIONED")


@router.get("/metrics/overview")
def overview():
    records = store.all_records()
    bands = defaultdict(int)
    for r in records:
        bands[r.health_band] += 1

    incidents = list(store.incidents.values())
    active = [i for i in incidents if i.status in ACTIVE]
    resolved = [i for i in incidents if i.status == "RESOLVED"]
    auto_closed = [i for i in incidents if i.status == "FALSE_POSITIVE"]

    at_risk = sum(i.revenue_risk.expected for i in active)
    protected = sum(i.impact.revenue_protected for i in incidents if i.impact)
    latencies = [i.detection_latency_seconds for i in incidents if i.detection_latency_seconds]
    dq = [r.data_quality.score for r in records]

    return ok(
        {
            "monitored": len(records),
            "healthy": bands["HEALTHY"],
            "warning": bands["WARNING"],
            "high_risk": bands["HIGH_RISK"],
            "critical": bands["CRITICAL"],
            "revenue_at_risk": round(at_risk, 2),
            "revenue_protected": round(protected, 2),
            "incidents_open": len(active),
            "incidents_resolved": len(resolved),
            "incidents_auto_closed": len(auto_closed),
            "avg_detection_seconds": int(sum(latencies) / len(latencies)) if latencies else 0,
            "manual_baseline_seconds": 31 * 3600,
            "data_quality_score": round(sum(dq) / len(dq) * 100, 1) if dq else 0.0,
            "data_quality_incidents": sum(1 for i in incidents if i.is_data_quality),
            "analysis_runs": store.analysis_runs,
        }
    )


@router.get("/metrics/timeseries")
def timeseries(days: int = Query(7, ge=2, le=30)):
    now = store.now()
    buckets: dict[str, dict] = {}
    for d in range(days - 1, -1, -1):
        day = (now - timedelta(days=d)).date().isoformat()
        buckets[day] = {"date": day, "at_risk": 0.0, "protected": 0.0, "incidents": 0}

    for incident in store.incidents.values():
        day = incident.detected_at.date().isoformat()
        if day in buckets:
            buckets[day]["incidents"] += 1
            buckets[day]["at_risk"] += (
                incident.impact.risk_at_detection if incident.impact else incident.revenue_risk.expected
            )
        if incident.impact and incident.impact.revenue_protected:
            resolved_at = incident.detected_at + timedelta(
                seconds=incident.impact.time_to_resolve_seconds or 0
            )
            rday = resolved_at.date().isoformat()
            if rday in buckets:
                buckets[rday]["protected"] += incident.impact.revenue_protected

    series = [
        {**b, "at_risk": round(b["at_risk"], 2), "protected": round(b["protected"], 2)}
        for b in buckets.values()
    ]
    return ok(series)


@router.get("/metrics/priority-queue")
def priority_queue(limit: int = 5):
    items = [i for i in store.incidents.values() if i.status in ACTIVE]
    items.sort(key=lambda i: -i.risk_score)
    return ok(
        [
            {
                "incident_id": i.incident_id,
                "campaign_id": i.campaign_id,
                "campaign_name": i.campaign_name,
                "advertiser": i.advertiser,
                "severity": i.severity,
                "priority": i.priority,
                "status": i.status,
                "revenue_at_risk": i.revenue_risk.expected,
                "health_score": i.health_score,
                "risk_score": i.risk_score,
                "primary_cause": i.diagnosis.primary_cause.label if i.diagnosis else None,
                "confidence": i.diagnosis.confidence if i.diagnosis else None,
                "is_data_quality": i.is_data_quality,
                "detected_at": i.detected_at.isoformat(),
            }
            for i in items[:limit]
        ]
    )


@router.get("/impact")
def impact_ledger():
    rows = []
    for i in store.incidents.values():
        if not i.impact or not i.impact.revenue_protected:
            continue
        rows.append(
            {
                "incident_id": i.incident_id,
                "campaign_name": i.campaign_name,
                "advertiser": i.advertiser,
                "severity": i.severity,
                "detected_at": i.detected_at.isoformat(),
                "risk_at_detection": i.impact.risk_at_detection,
                "revenue_protected": i.impact.revenue_protected,
                "impressions_recovered": i.impact.impressions_recovered,
                "time_to_detect_seconds": i.impact.time_to_detect_seconds,
                "time_to_resolve_seconds": i.impact.time_to_resolve_seconds,
                "outcome": i.impact.outcome,
            }
        )
    rows.sort(key=lambda r: -r["revenue_protected"])
    total_protected = sum(r["revenue_protected"] for r in rows)
    total_risk = sum(r["risk_at_detection"] for r in rows)
    outcomes = defaultdict(int)
    for r in rows:
        outcomes[r["outcome"]] += 1
    return ok(
        {
            "rows": rows,
            "total_protected": round(total_protected, 2),
            "total_identified": round(total_risk, 2),
            "recovery_rate": round(total_protected / total_risk * 100, 1) if total_risk else 0.0,
            "outcomes": dict(outcomes),
            "avg_detect_seconds": int(
                sum(r["time_to_detect_seconds"] for r in rows) / len(rows)
            ) if rows else 0,
            "avg_resolve_seconds": int(
                sum(r["time_to_resolve_seconds"] for r in rows) / len(rows)
            ) if rows else 0,
        }
    )


@router.get("/events/recent")
def recent_events(limit: int = 40):
    return ok(bus.recent(limit))


@router.get("/tools")
def tools():
    return ok(TOOL_DEFINITIONS)


@router.get("/settings")
def read_settings():
    cfg = get_settings()
    return ok(
        {
            "demo_mode": cfg.demo_mode,
            "dry_run": cfg.dry_run,
            "random_seed": cfg.random_seed,
            "llm_provider": cfg.llm_provider,
            "llm_configured": bool(cfg.openai_api_key or cfg.gemini_api_key),
            "health_weights": cfg.health_weights.model_dump(),
            "health_bands": cfg.health_bands.model_dump(),
            "anomaly": cfg.anomaly.model_dump(),
            "revenue_risk": cfg.revenue_risk.model_dump(),
            "current_window_hours": cfg.current_window_hours,
            "baseline_window_days": cfg.baseline_window_days,
            "integrations": [
                {"name": "Google Ad Manager", "status": "Mock adapter", "detail": "GAM delivery + line item data"},
                {"name": "SpringServe", "status": "Mock adapter", "detail": "Supply tags, fill, VAST errors"},
                {"name": "Athena", "status": "Mock adapter", "detail": "Historical baselines"},
                {"name": "RevGuard AI", "status": cfg.llm_provider, "detail": "Evidence-grounded synthesis"},
                {"name": "Slack", "status": "Dry run" if cfg.dry_run else "Live", "detail": "Block Kit payload"},
                {"name": "JIRA", "status": "Dry run" if cfg.dry_run else "Live", "detail": "REST v3 issue payload"},
            ],
        }
    )


@router.post("/settings/weights")
def update_weights(weights: dict = Body(...)):
    """Business rules are tunable at runtime -- the whole portfolio re-scores instantly."""
    cfg = get_settings()
    for key, value in weights.items():
        if hasattr(cfg.health_weights, key):
            setattr(cfg.health_weights, key, float(value))
    bus.publish("settings.updated", {"health_weights": cfg.health_weights.model_dump()})
    return ok(cfg.health_weights.model_dump())
