"""Slack Block Kit payload builder. DRY_RUN by default -- we return the payload and the
UI renders it as a Slack preview. Set SLACK_WEBHOOK_URL + DRY_RUN=false to actually post.
"""

from __future__ import annotations

from typing import Any

import httpx

from ..config import get_settings
from ..models import Incident

SEVERITY_EMOJI = {"CRITICAL": "🚨", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}


def build_payload(incident: Incident) -> dict[str, Any]:
    d = incident.diagnosis
    r = incident.recommendation
    risk = incident.revenue_risk
    emoji = SEVERITY_EMOJI.get(incident.severity, "🚨")

    fields = [
        {"type": "mrkdwn", "text": f"*Revenue at risk*\n💰 ${risk.expected:,.0f}"},
        {
            "type": "mrkdwn",
            "text": f"*Pacing*\n{incident.health_score:.0f} health · {incident.priority}",
        },
    ]
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} XPERI REVGUARD — {incident.severity}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{incident.campaign_name}*  `{incident.campaign_id}`"},
            "fields": fields,
        },
    ]

    if d:
        secondary = ", ".join(
            f"{c.label} — {c.confidence * 100:.0f}%" for c in d.secondary_causes[:2]
        )
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Primary suspected cause*\n🎯 {d.primary_cause.label} — "
                        f"{d.primary_cause.confidence * 100:.0f}%"
                        + (f"\n*Secondary*\n📺 {secondary}" if secondary else "")
                        + f"\n\n{d.narrative}"
                    ),
                },
            }
        )

    if r:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Recommended action*\n{r.title}\n"
                        f"*Potential recovery*\n${r.predicted_recovery.conservative:,.0f}–"
                        f"${r.predicted_recovery.worst_case:,.0f} "
                        f"(+{r.predicted_impression_gain:,} impressions)\n"
                        f"*Confidence*\n{r.confidence * 100:.0f}%"
                    ),
                },
            }
        )

    blocks.extend(
        [
            {
                "type": "actions",
                "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Investigate"},
                     "style": "primary", "value": incident.incident_id},
                    {"type": "button", "text": {"type": "plain_text", "text": "Create JIRA"},
                     "value": f"jira:{incident.incident_id}"},
                    {"type": "button", "text": {"type": "plain_text", "text": "View Campaign"},
                     "value": f"campaign:{incident.campaign_id}"},
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"Detected {incident.detected_at.strftime('%d %b %H:%M UTC')} · "
                            f"evidence-grounded: "
                            f"{'yes' if d and d.grounding_passed else 'n/a'} · simulated dataset"
                        ),
                    }
                ],
            },
        ]
    )
    return {"channel": "#ad-ops-alerts", "text": f"{incident.campaign_name} — {incident.severity}",
            "blocks": blocks}


def send(incident: Incident) -> dict[str, Any]:
    cfg = get_settings()
    payload = build_payload(incident)
    if cfg.dry_run or not cfg.slack_webhook_url:
        return {"dry_run": True, "delivered": False, "payload": payload}
    response = httpx.post(cfg.slack_webhook_url, json=payload, timeout=10.0)
    return {"dry_run": False, "delivered": response.is_success,
            "status_code": response.status_code, "payload": payload}
