"""Incident, analysis and action endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

from ..actions import jira, slack
from ..diagnosis import evidence_builder
from ..recommendations import what_if
from ..store.memory import store
from .common import ok

router = APIRouter(prefix="/api", tags=["incidents"])

ACTIVE = ("OPEN", "INVESTIGATING", "AWAITING_APPROVAL", "ACTIONED")


class WhatIfRequest(BaseModel):
    platforms: list[str] | None = None
    geos: list[str] | None = None
    devices: list[str] | None = None
    content_categories: list[str] | None = None


def _get(incident_id: str):
    incident = store.incidents.get(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


@router.post("/analysis/run")
def run_analysis(campaign_id: str | None = None):
    created = store.run_analysis(campaign_id)
    return ok(
        {
            "created": [i.model_dump(mode="json") for i in created],
            "open_incidents": sum(1 for i in store.incidents.values() if i.status in ACTIVE),
            "campaigns_scanned": 1 if campaign_id else len(store.world.campaigns),
        }
    )


@router.get("/incidents")
def list_incidents(
    status: str | None = None,
    severity: str | None = None,
    priority: str | None = None,
    active_only: bool = False,
    limit: int = Query(200, le=500),
):
    items = list(store.incidents.values())
    if active_only:
        items = [i for i in items if i.status in ACTIVE]
    if status:
        wanted = {s.strip().upper() for s in status.split(",")}
        items = [i for i in items if i.status in wanted]
    if severity:
        items = [i for i in items if i.severity == severity.upper()]
    if priority:
        items = [i for i in items if i.priority == priority.upper()]
    items.sort(key=lambda i: (-i.risk_score, i.detected_at))
    return ok([i.model_dump(mode="json") for i in items[:limit]], total=len(items))


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    incident = _get(incident_id)
    package = store.evidence.get(incident_id)
    return ok(
        {
            "incident": incident.model_dump(mode="json"),
            "evidence": package.model_dump(mode="json") if package else None,
            "trace": [t.model_dump(mode="json") for t in store.traces.get(incident_id, [])],
        }
    )


@router.get("/incidents/{incident_id}/evidence")
def get_evidence(incident_id: str):
    incident = _get(incident_id)
    package = store.evidence.get(incident_id)
    if package is None:
        record = store.record(incident.campaign_id)
        package = evidence_builder.build(record, store.campaign(incident.campaign_id))
    return ok(package.model_dump(mode="json"))


@router.post("/incidents/{incident_id}/diagnose")
def diagnose(incident_id: str):
    _get(incident_id)
    incident = store.diagnose(incident_id)
    package = store.evidence.get(incident_id)
    return ok(
        {
            "incident": incident.model_dump(mode="json"),
            "evidence": package.model_dump(mode="json") if package else None,
            "trace": [t.model_dump(mode="json") for t in store.traces.get(incident_id, [])],
        }
    )


@router.post("/incidents/{incident_id}/what-if")
def what_if_route(incident_id: str, body: WhatIfRequest):
    incident = _get(incident_id)
    record = store.record(incident.campaign_id)
    _, projected, _ = store.risk_for(record)
    proposed = {k: v for k, v in body.model_dump().items() if v is not None}
    result = what_if.evaluate(
        campaign=store.campaign(incident.campaign_id),
        record=record,
        proposed=proposed,
        projected_gap=projected,
    )
    result["predicted_recovery"] = result["predicted_recovery"].model_dump(mode="json")
    return ok(result)


@router.post("/incidents/{incident_id}/approve")
def approve(incident_id: str, actor: str = Body("ad.ops@demo", embed=True)):
    _get(incident_id)
    incident = store.approve(incident_id, actor)
    return ok(incident.model_dump(mode="json"))


@router.post("/incidents/{incident_id}/false-positive")
def false_positive(incident_id: str, actor: str = Body("ad.ops@demo", embed=True)):
    _get(incident_id)
    return ok(store.mark_false_positive(incident_id, actor).model_dump(mode="json"))


@router.get("/incidents/{incident_id}/impact")
def impact(incident_id: str):
    incident = _get(incident_id)
    return ok(incident.impact.model_dump(mode="json") if incident.impact else None)


@router.get("/incidents/{incident_id}/audit")
def audit(incident_id: str):
    incident = _get(incident_id)
    return ok([a.model_dump(mode="json") for a in incident.audit])


@router.post("/actions/slack/preview")
def slack_preview(incident_id: str = Body(..., embed=True)):
    return ok(slack.build_payload(_get(incident_id)))


@router.post("/actions/slack/send")
def slack_send(incident_id: str = Body(..., embed=True)):
    incident = _get(incident_id)
    result = slack.send(incident)
    store.log_integration(
        incident_id,
        "Slack alert posted" if not result["dry_run"] else "Slack alert prepared (dry run)",
        "#ad-ops-alerts",
    )
    return ok(result)


@router.post("/actions/jira/preview")
def jira_preview(incident_id: str = Body(..., embed=True)):
    incident = _get(incident_id)
    package = store.evidence.get(incident_id)
    labels = [i.label for i in package.items] if package else None
    return ok(jira.build_payload(incident, labels))


@router.post("/actions/jira/create")
def jira_create(incident_id: str = Body(..., embed=True)):
    incident = _get(incident_id)
    package = store.evidence.get(incident_id)
    labels = [i.label for i in package.items] if package else None
    result = jira.create(incident, labels)
    store.log_integration(
        incident_id,
        f"JIRA {result['issue_key']} {'created' if result.get('created') else 'prepared (dry run)'}",
        result["issue_key"],
    )
    return ok(result)
