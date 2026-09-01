"""The in-memory Guardian store: world + simulated clock + pipeline + incident ledger."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from ..analytics import anomaly, pacing, prioritization, revenue_risk
from ..config import get_settings
from ..diagnosis import investigator
from ..events.bus import bus
from ..ingestion import normalizer
from ..models import (
    AuditLogEntry,
    Campaign,
    CampaignHealthRecord,
    ImpactRecord,
    Incident,
    TimelineEvent,
    ToolCall,
)
from ..recommendations import engine as rec_engine
from .world import World, build_world

RESOLVED_SEED_COUNT = 24
PROJECTION_HORIZON_HOURS = 168  # exposure is projected 7 days out, or to flight end


class GuardianStore:
    def __init__(self) -> None:
        self.world: World = build_world()
        self.clock: datetime = self.world.sim_start
        self.speed: int = 0  # 0 = paused
        self.incidents: dict[str, Incident] = {}
        self.evidence: dict[str, object] = {}
        self.traces: dict[str, list[ToolCall]] = {}
        self._counter = 1000
        self._last_analysis: datetime | None = None
        self.analysis_runs = 0
        self._seed_resolved_ledger()

    # ---------------------------------------------------------------- clock

    def now(self) -> datetime:
        return self.clock

    def set_clock(self, ts: datetime) -> None:
        lo = self.world.origin + timedelta(hours=1)
        hi = self.world.ts_for(self.world.hours - 1)
        self.clock = max(lo, min(hi, ts))

    def advance(self, minutes: int) -> None:
        self.set_clock(self.clock + timedelta(minutes=minutes))

    def reset(self) -> None:
        self.world = build_world()
        self.clock = self.world.sim_start
        self.speed = 0
        self.incidents.clear()
        self.evidence.clear()
        self.traces.clear()
        self._counter = 1000
        self.analysis_runs = 0
        self._seed_resolved_ledger()
        bus.publish("world.reset", {"sim_clock": self.clock.isoformat()})

    # ---------------------------------------------------------------- records

    def campaign(self, campaign_id: str) -> Campaign:
        return self.world.campaigns[campaign_id]

    def record(self, campaign_id: str, at: datetime | None = None) -> CampaignHealthRecord:
        return normalizer.build_record(self.world, campaign_id, at or self.clock)

    def all_records(self) -> list[CampaignHealthRecord]:
        at = self.clock
        return [normalizer.build_record(self.world, cid, at) for cid in self.world.campaigns]

    def risk_for(self, record: CampaignHealthRecord):
        s = self.world.series[record.campaign_id]
        remaining = normalizer.remaining_hours(self.world, record.campaign_id, self.clock)
        realized = max(0.0, record.expected_impressions - record.actual_impressions)
        # Project over the next 7 days or to flight end, whichever comes first.
        horizon = min(remaining, PROJECTION_HORIZON_HOURS)
        projected = pacing.projected_end_of_flight_gap(
            s.required_rate, record.pacing_pct, horizon
        )
        return revenue_risk.compute(
            realized_gap=realized, projected_gap=projected, ecpm=record.ecpm
        ), projected, remaining

    # ---------------------------------------------------------------- pipeline

    def run_analysis(self, campaign_id: str | None = None) -> list[Incident]:
        ids = [campaign_id] if campaign_id else list(self.world.campaigns)
        created: list[Incident] = []
        prev_at = self.clock - timedelta(hours=1)

        for cid in ids:
            record = self.record(cid)
            previous = normalizer.build_record(self.world, cid, prev_at)
            result = anomaly.detect(record, previous)

            existing = self._open_incident_for(cid)
            if not result.fired:
                if existing and existing.status in ("OPEN", "INVESTIGATING"):
                    self._auto_close(existing, record)
                continue

            if existing:
                self._refresh(existing, record)
                continue

            incident = self._create(record, result.signals)
            created.append(incident)

        self.analysis_runs += 1
        self._last_analysis = self.clock
        self._refresh_impacts()
        if created:
            bus.publish(
                "analysis.completed",
                {"created": len(created), "sim_clock": self.clock.isoformat()},
            )
        return created

    def _open_incident_for(self, campaign_id: str) -> Incident | None:
        for inc in self.incidents.values():
            if inc.campaign_id == campaign_id and inc.status not in ("RESOLVED", "FALSE_POSITIVE"):
                return inc
        return None

    def _create(self, record: CampaignHealthRecord, signals: list[str]) -> Incident:
        self._counter += 1
        incident_id = f"INC-{self._counter}"
        risk, projected, remaining = self.risk_for(record)
        is_dq = record.data_quality.verdict == "BAD"
        severity = prioritization.severity_for(record.health_score, is_dq)
        flight = normalizer.flight_hours(self.world, record.campaign_id)
        score = prioritization.risk_score(
            expected_risk=risk.expected,
            severity=severity,
            confidence=0.9,
            urgency_value=prioritization.urgency(remaining, flight),
        )

        series = self.world.series[record.campaign_id]
        onset = self.world.ts_for(series.onset_idx) if series.onset_idx is not None else None
        detected = self.clock
        if onset:
            detected = min(self.clock, onset + timedelta(hours=2, minutes=18))
        latency = int((detected - onset).total_seconds()) if onset else 0

        incident = Incident(
            incident_id=incident_id,
            campaign_id=record.campaign_id,
            campaign_name=record.campaign_name,
            advertiser=record.advertiser,
            severity=severity,
            priority=prioritization.priority_for(score),
            status="OPEN",
            detected_at=detected,
            signals=signals,
            health_score=record.health_score,
            revenue_risk=risk,
            risk_score=score,
            is_data_quality=is_dq,
            detection_latency_seconds=latency,
            onset_at=onset,
            timeline=[
                TimelineEvent(
                    ts=onset or detected,
                    label="Degradation onset",
                    detail="First window where signals departed from baseline.",
                    kind="signal",
                ),
                TimelineEvent(
                    ts=detected,
                    label=f"{incident_id} created ({severity})",
                    detail=f"{len(signals)} agreeing signals sustained: {', '.join(signals)}",
                    kind="system",
                ),
            ],
            impact=ImpactRecord(
                incident_id=incident_id,
                risk_at_detection=risk.expected,
                risk_timeline=[{"ts": detected.isoformat(), "risk": risk.expected}],
                time_to_detect_seconds=latency,
            ),
        )
        self.incidents[incident_id] = incident
        bus.publish(
            "incident.created",
            {
                "incident_id": incident_id,
                "campaign_id": record.campaign_id,
                "campaign_name": record.campaign_name,
                "severity": severity,
                "priority": incident.priority,
                "revenue_risk": risk.expected,
                "is_data_quality": is_dq,
            },
        )
        return incident

    def _record_risk_point(self, incident: Incident, risk_value: float) -> None:
        """One point per simulated timestamp, so the burn-down chart stays readable."""
        impact = incident.impact
        if impact is None:
            return
        ts = self.clock.isoformat()
        if impact.risk_timeline and impact.risk_timeline[-1]["ts"] == ts:
            impact.risk_timeline[-1]["risk"] = risk_value
            return
        impact.risk_timeline.append({"ts": ts, "risk": risk_value})
        if len(impact.risk_timeline) > 120:
            del impact.risk_timeline[:-120]

    def _refresh(self, incident: Incident, record: CampaignHealthRecord) -> None:
        risk, _, remaining = self.risk_for(record)
        incident.revenue_risk = risk
        incident.health_score = record.health_score
        if incident.impact:
            self._record_risk_point(incident, risk.expected)
            self._settle(incident, record)

    def _auto_close(self, incident: Incident, record: CampaignHealthRecord) -> None:
        incident.status = "FALSE_POSITIVE"
        incident.timeline.append(
            TimelineEvent(
                ts=self.clock,
                label="Auto-closed: signals no longer agree",
                detail="Metrics returned inside the expected envelope without intervention.",
                kind="system",
            )
        )
        bus.publish(
            "incident.updated",
            {"incident_id": incident.incident_id, "status": incident.status},
        )

    def _refresh_impacts(self) -> None:
        for incident in self.incidents.values():
            if incident.status not in ("ACTIONED", "AWAITING_APPROVAL"):
                continue
            record = self.record(incident.campaign_id)
            risk, _, _ = self.risk_for(record)
            incident.revenue_risk = risk
            incident.health_score = record.health_score
            if incident.impact:
                self._record_risk_point(incident, risk.expected)
                self._settle(incident, record)

    def _settle(self, incident: Incident, record: CampaignHealthRecord) -> None:
        impact = incident.impact
        if impact is None or incident.status != "ACTIONED":
            return
        recovered = max(0.0, impact.risk_at_detection - incident.revenue_risk.expected)
        impact.revenue_protected = round(recovered, 2)
        impact.impressions_recovered = int(recovered / max(0.01, record.ecpm) * 1000)
        ratio = recovered / max(1.0, impact.risk_at_detection)
        if incident.revenue_risk.expected <= impact.risk_at_detection * 0.12:
            impact.outcome = "RECOVERED"
            incident.status = "RESOLVED"
            impact.time_to_resolve_seconds = int(
                (self.clock - incident.detected_at).total_seconds()
            )
            incident.timeline.append(
                TimelineEvent(
                    ts=self.clock,
                    label=f"Resolved - ${impact.revenue_protected:,.0f} protected",
                    detail=f"{impact.impressions_recovered:,} impressions recovered.",
                    kind="impact",
                )
            )
            bus.publish(
                "impact.recorded",
                {
                    "incident_id": incident.incident_id,
                    "revenue_protected": impact.revenue_protected,
                    "campaign_name": incident.campaign_name,
                },
            )
        elif ratio > 0.15:
            impact.outcome = "PARTIAL"

    # ---------------------------------------------------------------- diagnosis / action

    def diagnose(self, incident_id: str) -> Incident:
        incident = self.incidents[incident_id]
        record = self.record(incident.campaign_id)
        campaign = self.campaign(incident.campaign_id)
        diagnosis, package, trace = investigator.investigate(incident_id, record, campaign)

        incident.diagnosis = diagnosis
        self.evidence[incident_id] = package
        self.traces[incident_id] = trace
        if incident.status == "OPEN":
            incident.status = "INVESTIGATING"
        incident.timeline.append(
            TimelineEvent(
                ts=self.clock,
                label=f"AI diagnosis: {diagnosis.primary_cause.label}",
                detail=(
                    f"{diagnosis.confidence * 100:.0f}% confidence, "
                    f"{len(diagnosis.evidence_used)} evidence items cited, "
                    f"grounding {'passed' if diagnosis.grounding_passed else 'FAILED'}"
                ),
                kind="ai",
            )
        )

        _, projected, _ = self.risk_for(record)
        incident.recommendation = rec_engine.build(
            incident_id=incident_id,
            cause=diagnosis.primary_cause.cause,
            record=record,
            campaign=campaign,
            projected_gap=projected,
            confidence=diagnosis.confidence,
        )
        incident.status = "AWAITING_APPROVAL"
        incident.timeline.append(
            TimelineEvent(
                ts=self.clock,
                label=f"Recommendation: {incident.recommendation.title}",
                detail=(
                    f"+{incident.recommendation.predicted_impression_gain:,} impressions, "
                    f"${incident.recommendation.predicted_recovery.conservative:,.0f}-"
                    f"${incident.recommendation.predicted_recovery.worst_case:,.0f} recovery"
                ),
                kind="ai",
            )
        )
        bus.publish(
            "incident.updated",
            {"incident_id": incident_id, "status": incident.status,
             "primary_cause": diagnosis.primary_cause.label},
        )
        return incident

    def approve(self, incident_id: str, actor: str = "ad.ops@demo") -> Incident:
        incident = self.incidents[incident_id]
        before = {"status": incident.status}
        if incident.recommendation and incident.recommendation.action_type != "INVESTIGATE_ONLY":
            self.world.apply_remediation(incident.campaign_id, self.clock)
        incident.status = "ACTIONED"
        incident.audit.append(
            AuditLogEntry(
                ts=self.clock,
                actor=actor,
                action="APPROVE_RECOMMENDATION",
                before=before,
                after={"status": incident.status,
                       "applied": incident.recommendation.title if incident.recommendation else ""},
                incident_id=incident_id,
            )
        )
        incident.timeline.append(
            TimelineEvent(
                ts=self.clock,
                label=f"Approved by {actor}",
                detail=incident.recommendation.title if incident.recommendation else "",
                kind="human",
            )
        )
        bus.publish(
            "action.executed",
            {"incident_id": incident_id, "campaign_name": incident.campaign_name,
             "action": incident.recommendation.title if incident.recommendation else ""},
        )
        return incident

    def mark_false_positive(self, incident_id: str, actor: str = "ad.ops@demo") -> Incident:
        incident = self.incidents[incident_id]
        before = {"status": incident.status}
        incident.status = "FALSE_POSITIVE"
        incident.audit.append(
            AuditLogEntry(ts=self.clock, actor=actor, action="MARK_FALSE_POSITIVE",
                          before=before, after={"status": incident.status},
                          incident_id=incident_id)
        )
        incident.timeline.append(
            TimelineEvent(ts=self.clock, label=f"Marked false positive by {actor}", kind="human")
        )
        bus.publish("incident.updated", {"incident_id": incident_id, "status": incident.status})
        return incident

    def log_integration(self, incident_id: str, label: str, detail: str) -> None:
        incident = self.incidents[incident_id]
        incident.timeline.append(
            TimelineEvent(ts=self.clock, label=label, detail=detail, kind="integration")
        )
        incident.audit.append(
            AuditLogEntry(ts=self.clock, actor="revguard", action=label,
                          after={"detail": detail}, incident_id=incident_id)
        )

    # ---------------------------------------------------------------- seeded ledger

    def _seed_resolved_ledger(self) -> None:
        """Historical incidents already resolved today, so the impact ledger has substance.

        Clearly attributed to the simulated dataset -- these are demo figures.
        """
        cfg = get_settings()
        rng = random.Random(cfg.random_seed + 99)
        ids = [c for c in self.world.campaigns if c != self.world.golden_id]
        for n in range(RESOLVED_SEED_COUNT):
            cid = ids[rng.randrange(len(ids))]
            campaign = self.world.campaigns[cid]
            self._counter += 1
            incident_id = f"INC-{self._counter}"
            detected = self.clock - timedelta(hours=rng.uniform(6, 155))
            at_risk = round(rng.uniform(900, 6800), 2)
            protected = round(at_risk * rng.uniform(0.55, 0.94), 2)
            resolve_secs = int(rng.uniform(2400, 14400))
            self.incidents[incident_id] = Incident(
                incident_id=incident_id,
                campaign_id=cid,
                campaign_name=campaign.name,
                advertiser=campaign.advertiser,
                severity=rng.choice(["CRITICAL", "HIGH", "MEDIUM"]),
                priority=rng.choice(["P0", "P1", "P2"]),
                status="RESOLVED",
                detected_at=detected,
                signals=["pacing_down", "fill_rate_down"],
                health_score=round(rng.uniform(22, 58), 1),
                revenue_risk=revenue_risk.compute(
                    realized_gap=0.0,
                    projected_gap=at_risk / campaign.ecpm * 1000,
                    ecpm=campaign.ecpm,
                ),
                risk_score=round(rng.uniform(0.1, 0.6), 3),
                detection_latency_seconds=int(rng.uniform(3000, 12000)),
                onset_at=detected - timedelta(seconds=int(rng.uniform(3000, 12000))),
                timeline=[
                    TimelineEvent(ts=detected, label=f"{incident_id} created", kind="system"),
                    TimelineEvent(
                        ts=detected + timedelta(seconds=resolve_secs),
                        label=f"Resolved - ${protected:,.0f} protected",
                        kind="impact",
                    ),
                ],
                impact=ImpactRecord(
                    incident_id=incident_id,
                    risk_at_detection=at_risk,
                    revenue_protected=protected,
                    impressions_recovered=int(protected / campaign.ecpm * 1000),
                    time_to_detect_seconds=int(rng.uniform(3000, 12000)),
                    time_to_resolve_seconds=resolve_secs,
                    outcome="RECOVERED" if protected / at_risk > 0.7 else "PARTIAL",
                    risk_timeline=[
                        {"ts": (detected + timedelta(seconds=int(resolve_secs * f))).isoformat(),
                         "risk": round(at_risk * (1 - f), 2)}
                        for f in (0.0, 0.35, 0.7, 1.0)
                    ],
                ),
            )


store = GuardianStore()
