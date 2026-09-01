"""Guardian Copilot: answers from live monitoring state, with a visible tool trace.

The deterministic answer is computed by the analytics layer. When a real LLM is
configured it receives exactly the same context and rewrites it in prose -- it never
gets to invent a figure.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..models import ToolCall
from ..store.memory import store
from ..tools.definitions import run_tool
from .prompts import COPILOT_SYSTEM_PROMPT
from .provider import get_provider

ACTIVE = ("OPEN", "INVESTIGATING", "AWAITING_APPROVAL", "ACTIONED")

SUGGESTIONS = [
    "What is my biggest revenue risk right now?",
    "Why is Acme Sports CTV underdelivering?",
    "How much revenue have we protected?",
    "Which platform has the worst VAST errors?",
    "How many campaigns are critical?",
]


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _duration(seconds: int) -> str:
    h, m = divmod(int(seconds) // 60, 60)
    return f"{h}h {m}m" if h else f"{m}m"


def _find_campaign(question: str) -> str | None:
    q = question.lower()
    best, best_len = None, 0
    for cid, campaign in store.world.campaigns.items():
        for token in (campaign.name.lower(), campaign.advertiser.lower(), cid.lower()):
            if len(token) > 3 and token in q and len(token) > best_len:
                best, best_len = cid, len(token)
    return best


def answer(question: str) -> dict[str, Any]:
    q = question.lower()
    trace: list[ToolCall] = []
    context: dict[str, Any] = {"question": question}
    campaign_id = _find_campaign(question)

    if any(k in q for k in ("protect", "recovered", "saved", "impact")):
        result, call = run_tool("get_impact_summary", _impact_summary, {})
        trace.append(call)
        context["impact"] = result
        text = (
            f"We have protected {_money(result['total_protected'])} across "
            f"{result['resolved']} resolved incidents, from "
            f"{_money(result['total_identified'])} identified as at risk "
            f"({result['recovery_rate']:.0f}% recovery rate). Average time from onset to "
            f"alert is {_duration(result['avg_detect_seconds'])}."
        )

    elif campaign_id and any(k in q for k in ("why", "cause", "wrong", "underdeliver", "problem")):
        text = _diagnose_campaign(campaign_id, trace, context)

    elif campaign_id:
        text = _campaign_summary(campaign_id, trace, context)

    elif any(k in q for k in ("vast", "error", "platform", "playback")):
        result, call = run_tool("get_vast_errors", _worst_vast, {})
        trace.append(call)
        context["vast"] = result
        if result["rows"]:
            top = result["rows"][0]
            text = (
                f"{top['platform']} has the worst playback errors: {top['error_rate']:.2f}% "
                f"against a {top['baseline']:.2f}% baseline on {top['campaign_name']} "
                f"({top['campaign_id']}), dominated by {top['code']}. "
                f"{result['affected']} campaigns currently show elevated VAST errors."
            )
        else:
            text = "No campaign currently shows a VAST error rate above its baseline."

    elif any(k in q for k in ("critical", "health", "how many", "portfolio", "status")):
        result, call = run_tool("get_portfolio_health", _portfolio, {})
        trace.append(call)
        context["portfolio"] = result
        text = (
            f"Monitoring {result['monitored']} campaigns: {result['healthy']} healthy, "
            f"{result['warning']} warning, {result['high_risk']} high risk, "
            f"{result['critical']} critical. {result['open_incidents']} incidents are open "
            f"with {_money(result['revenue_at_risk'])} at risk."
        )

    else:
        result, call = run_tool("list_open_incidents", lambda: _top_incidents(3), {"limit": 3})
        trace.append(call)
        context["incidents"] = result
        if result:
            top = result[0]
            text = (
                f"Your largest exposure is {top['campaign_name']} ({top['campaign_id']}) at "
                f"{_money(top['revenue_at_risk'])}, {top['severity']} / {top['priority']}"
                + (f", primary cause {top['primary_cause']}." if top["primary_cause"] else
                   ". Run a diagnosis to identify the root cause.")
                + f" {len(result)} incidents are in the priority queue."
            )
        else:
            text = (
                "No open incidents right now. Run an analysis or inject a scenario from the "
                "demo control bar to generate one."
            )

    context["deterministic_answer"] = text
    provider = get_provider()
    try:
        final = provider.complete_text(COPILOT_SYSTEM_PROMPT, json.dumps(context, default=str))
    except Exception:
        final = text
    if not _numbers_grounded(final, text):
        final = text

    return {
        "answer": final.strip(),
        "trace": [t.model_dump(mode="json") for t in trace],
        "generated_by": provider.name,
        "suggestions": SUGGESTIONS,
    }


NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


def _numbers_grounded(candidate: str, grounded: str) -> bool:
    allowed = set(NUMBER_RE.findall(grounded))
    return all(n in allowed for n in NUMBER_RE.findall(candidate))


def _impact_summary() -> dict[str, Any]:
    rows = [i for i in store.incidents.values() if i.impact and i.impact.revenue_protected]
    protected = sum(i.impact.revenue_protected for i in rows)
    identified = sum(i.impact.risk_at_detection for i in rows)
    latencies = [i.detection_latency_seconds for i in store.incidents.values() if i.detection_latency_seconds]
    return {
        "total_protected": round(protected, 2),
        "total_identified": round(identified, 2),
        "recovery_rate": round(protected / identified * 100, 1) if identified else 0.0,
        "resolved": len(rows),
        "avg_detect_seconds": int(sum(latencies) / len(latencies)) if latencies else 0,
    }


def _top_incidents(limit: int) -> list[dict[str, Any]]:
    items = [i for i in store.incidents.values() if i.status in ACTIVE]
    items.sort(key=lambda i: -i.risk_score)
    return [
        {
            "incident_id": i.incident_id,
            "campaign_id": i.campaign_id,
            "campaign_name": i.campaign_name,
            "severity": i.severity,
            "priority": i.priority,
            "revenue_at_risk": i.revenue_risk.expected,
            "primary_cause": i.diagnosis.primary_cause.label if i.diagnosis else None,
        }
        for i in items[:limit]
    ]


def _portfolio() -> dict[str, Any]:
    records = store.all_records()
    active = [i for i in store.incidents.values() if i.status in ACTIVE]
    return {
        "monitored": len(records),
        "healthy": sum(1 for r in records if r.health_band == "HEALTHY"),
        "warning": sum(1 for r in records if r.health_band == "WARNING"),
        "high_risk": sum(1 for r in records if r.health_band == "HIGH_RISK"),
        "critical": sum(1 for r in records if r.health_band == "CRITICAL"),
        "open_incidents": len(active),
        "revenue_at_risk": round(sum(i.revenue_risk.expected for i in active), 2),
    }


def _worst_vast() -> dict[str, Any]:
    rows = []
    for record in store.all_records():
        if record.baseline_error_rate and record.error_rate >= record.baseline_error_rate * 1.8:
            rows.append(
                {
                    "campaign_id": record.campaign_id,
                    "campaign_name": record.campaign_name,
                    "platform": record.worst_platform,
                    "code": record.worst_vast_code,
                    "error_rate": record.error_rate,
                    "baseline": record.baseline_error_rate,
                }
            )
    rows.sort(key=lambda r: -(r["error_rate"] / max(0.001, r["baseline"])))
    return {"rows": rows[:5], "affected": len(rows)}


def _campaign_summary(campaign_id: str, trace: list[ToolCall], context: dict) -> str:
    record, call = run_tool(
        "get_campaign_metrics",
        lambda: store.record(campaign_id).model_dump(mode="json"),
        {"campaign_id": campaign_id},
    )
    trace.append(call)
    risk, call2 = run_tool(
        "calculate_revenue_risk",
        lambda: store.risk_for(store.record(campaign_id))[0].model_dump(mode="json"),
        {"campaign_id": campaign_id},
    )
    trace.append(call2)
    context["campaign"] = record
    context["revenue_risk"] = risk
    return (
        f"{record['campaign_name']} is {record['health_band'].replace('_', ' ').lower()} at "
        f"{record['health_score']:.0f}/100. Delivery rate is {record['pacing_pct']:.0f}% of plan, "
        f"fill {record['fill_rate']:.1f}% vs {record['baseline_fill_rate']:.1f}% baseline, "
        f"VAST errors {record['error_rate']:.2f}% vs {record['baseline_error_rate']:.2f}%. "
        f"Estimated revenue at risk {_money(risk['expected'])}."
    )


def _diagnose_campaign(campaign_id: str, trace: list[ToolCall], context: dict) -> str:
    base = _campaign_summary(campaign_id, trace, context)
    incident = store._open_incident_for(campaign_id)
    if incident is None:
        return base + " No open incident: signals do not currently agree on a fault."
    if incident.diagnosis is None:
        _, call = run_tool(
            "synthesize_diagnosis",
            lambda: store.diagnose(incident.incident_id),
            {"incident_id": incident.incident_id},
        )
        trace.append(call)
    d = store.incidents[incident.incident_id].diagnosis
    if d is None:
        return base
    context["diagnosis"] = d.model_dump(mode="json")
    secondary = ", ".join(f"{c.label} {c.confidence * 100:.0f}%" for c in d.secondary_causes[:2])
    return (
        f"{base} Primary cause is {d.primary_cause.label.lower()} at "
        f"{d.primary_cause.confidence * 100:.0f}% of weighted evidence"
        + (f", followed by {secondary}." if secondary else ".")
        + f" {d.narrative} See {incident.incident_id}."
    )
