"""MCP-shaped tool registry.

These definitions are already MCP-compatible JSON Schema. Exposing them as an MCP
server is a transport change, not a rewrite -- the handlers below are the same ones
the copilot and the investigator call today.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from ..models import ToolCall

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_campaign_metrics",
        "description": "Current normalized health record for one campaign.",
        "inputSchema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}},
            "required": ["campaign_id"],
        },
    },
    {
        "name": "get_historical_pacing",
        "description": "Hourly delivery vs required rate for the trailing N hours.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "hours": {"type": "integer", "default": 48},
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "get_supply_tag_health",
        "description": "Fill and error rates for the supply tags mapped to a campaign.",
        "inputSchema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}},
            "required": ["campaign_id"],
        },
    },
    {
        "name": "get_vast_errors",
        "description": "VAST error code breakdown for a campaign or platform.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "platform": {"type": "string"},
            },
        },
    },
    {
        "name": "calculate_revenue_risk",
        "description": "Three-point estimated revenue at risk for a campaign.",
        "inputSchema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}},
            "required": ["campaign_id"],
        },
    },
    {
        "name": "list_open_incidents",
        "description": "Open incidents ranked by risk score.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 5}},
        },
    },
    {
        "name": "get_impact_summary",
        "description": "Revenue protected, incidents resolved, detection latency.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "synthesize_diagnosis",
        "description": "Evidence-grounded root cause synthesis for an incident.",
        "inputSchema": {
            "type": "object",
            "properties": {"incident_id": {"type": "string"}},
            "required": ["incident_id"],
        },
    },
    {
        "name": "create_jira_ticket",
        "description": "Build (and optionally create) a JIRA issue for an incident.",
        "inputSchema": {
            "type": "object",
            "properties": {"incident_id": {"type": "string"}},
            "required": ["incident_id"],
        },
    },
]


def run_tool(name: str, handler: Callable[[], Any], arguments: dict[str, Any]) -> tuple[Any, ToolCall]:
    t0 = time.perf_counter()
    ok, preview, result = True, "", None
    try:
        result = handler()
        preview = _preview(result)
    except Exception as exc:
        ok, preview = False, f"{type(exc).__name__}: {exc}"
    return result, ToolCall(
        name=name,
        arguments=arguments,
        duration_ms=int((time.perf_counter() - t0) * 1000),
        ok=ok,
        result_preview=preview,
    )


def _preview(value: Any) -> str:
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    if isinstance(value, dict):
        return ", ".join(list(value)[:4])
    return str(value)[:120]
