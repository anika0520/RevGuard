"""Orchestrates a diagnosis: evidence -> deterministic rules -> ranking -> AI synthesis
-> grounding validation. Emits a tool trace so the UI can show exactly what happened.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from ..ai import grounding, prompts
from ..ai.provider import FALLBACK, get_provider
from ..models import (
    Campaign,
    CampaignHealthRecord,
    Diagnosis,
    EvidencePackage,
    ToolCall,
)
from . import cause_scoring, evidence_builder, root_cause_rules


def investigate(
    incident_id: str, record: CampaignHealthRecord, campaign: Campaign
) -> tuple[Diagnosis, EvidencePackage, list[ToolCall]]:
    trace: list[ToolCall] = []

    t0 = time.perf_counter()
    package = evidence_builder.build(record, campaign)
    trace.append(
        ToolCall(
            name="build_evidence_package",
            arguments={"campaign_id": record.campaign_id, "window": package.window},
            duration_ms=int((time.perf_counter() - t0) * 1000),
            result_preview=f"{len(package.items)} evidence items",
        )
    )

    t0 = time.perf_counter()
    hits = root_cause_rules.evaluate(record, package)
    causes = cause_scoring.rank(hits)
    trace.append(
        ToolCall(
            name="evaluate_root_cause_rules",
            arguments={"rules_evaluated": len(root_cause_rules.RULES)},
            duration_ms=int((time.perf_counter() - t0) * 1000),
            result_preview=", ".join(f"{c.cause} {c.confidence:.2f}" for c in causes) or "none",
        )
    )

    confidence, breakdown = cause_scoring.overall_confidence(causes, package)
    # Rule-derived confidences are legitimate grounded values the narrative may quote.
    package.facts["candidate_confidence_pct"] = [
        round(c.confidence * 100) for c in causes
    ]
    package.facts["overall_confidence_pct"] = round(confidence * 100)

    provider = get_provider()
    system = prompts.SYSTEM_PROMPT
    user = prompts.build_user_prompt(package, causes)

    result, generated_by, model, grounding_result = _call_with_grounding(
        provider, system, user, package, trace
    )

    now = datetime.now(timezone.utc)
    if not causes:
        from ..models import CandidateCause

        primary = CandidateCause(
            cause="DATA_QUALITY" if record.data_quality.verdict != "OK" else "SUPPLY_SHORTAGE",
            label="Insufficient evidence",
            weight=0.0,
            confidence=0.0,
            evidence_ids=[i.id for i in package.items[:1]],
            explanation="No rule met its evidence threshold.",
        )
        secondary = []
    else:
        primary, secondary = causes[0], causes[1:]

    return (
        Diagnosis(
            incident_id=incident_id,
            primary_cause=primary,
            secondary_causes=secondary,
            confidence=confidence,
            confidence_breakdown=breakdown,
            narrative=result["narrative"],
            recommended_action_summary=result.get("recommended_action_summary", ""),
            evidence_used=grounding_result.citations or result.get("evidence_cited", []),
            generated_by=generated_by,
            model=model,
            generated_at=now,
            grounding_passed=grounding_result.passed,
            grounding_notes=grounding_result.violations,
            insufficient_evidence=bool(result.get("insufficient_evidence")),
        ),
        package,
        trace,
    )


def _call_with_grounding(provider, system: str, user: str, package, trace: list[ToolCall]):
    """One attempt, one retry with the violations appended, then deterministic fallback."""
    attempt_user = user
    for attempt in range(2):
        t0 = time.perf_counter()
        try:
            result = provider.complete_json(system, attempt_user)
        except Exception as exc:  # network/parse failure -> fall back, never break the demo
            trace.append(
                ToolCall(
                    name="synthesize_diagnosis",
                    arguments={"provider": provider.name, "attempt": attempt + 1},
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                    ok=False,
                    result_preview=f"{type(exc).__name__}: {exc}",
                )
            )
            break

        checked = grounding.validate(
            result.get("narrative", ""), package, result.get("evidence_cited")
        )
        trace.append(
            ToolCall(
                name="synthesize_diagnosis",
                arguments={"provider": provider.name, "attempt": attempt + 1},
                duration_ms=int((time.perf_counter() - t0) * 1000),
                ok=checked.passed,
                result_preview=(
                    "grounded" if checked.passed else "; ".join(checked.violations[:2])
                ),
            )
        )
        if checked.passed:
            return result, provider.name, getattr(provider, "model", None), checked
        attempt_user = (
            f"{user}\n\nYour previous response was REJECTED by the grounding validator:\n"
            + "\n".join(f"- {v}" for v in checked.violations)
            + "\nRewrite using only values present in the evidence package."
        )

    t0 = time.perf_counter()
    result = FALLBACK.complete_json(system, user)
    checked = grounding.validate(result["narrative"], package, result.get("evidence_cited"))
    trace.append(
        ToolCall(
            name="synthesize_diagnosis",
            arguments={"provider": "deterministic", "reason": "grounding_fallback"},
            duration_ms=int((time.perf_counter() - t0) * 1000),
            ok=checked.passed,
            result_preview="deterministic fallback (grounded by construction)",
        )
    )
    return result, "deterministic", None, checked
