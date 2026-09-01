"""Domain models. Every downstream component speaks only these types."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------------------
# Campaign
# --------------------------------------------------------------------------------------

CampaignType = Literal["CTV", "Sports", "Entertainment", "News", "Kids", "Movies", "Gaming"]
HealthBand = Literal["HEALTHY", "WARNING", "HIGH_RISK", "CRITICAL"]
Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
Priority = Literal["P0", "P1", "P2", "P3"]
IncidentStatus = Literal[
    "OPEN", "INVESTIGATING", "AWAITING_APPROVAL", "ACTIONED", "RESOLVED", "FALSE_POSITIVE"
]
CauseCode = Literal[
    "TARGETING_RESTRICTION",
    "SUPPLY_SHORTAGE",
    "VAST_PLAYBACK_ERRORS",
    "GAM_COMPETITION",
    "CREATIVE_ISSUE",
    "FREQUENCY_CAP",
    "DATA_QUALITY",
    "BUDGET_PACING",
]
ActionType = Literal[
    "EXPAND_TARGETING",
    "PAUSE_TAG",
    "RAISE_PRIORITY",
    "ADJUST_FREQ_CAP",
    "REPLACE_CREATIVE",
    "INVESTIGATE_ONLY",
]


class Targeting(BaseModel):
    geos: list[str] = []
    devices: list[str] = []
    platforms: list[str] = []
    content_categories: list[str] = []
    frequency_cap: Optional[int] = None
    last_changed_at: Optional[datetime] = None


class Campaign(BaseModel):
    campaign_id: str
    line_item_id: str
    name: str
    advertiser: str
    campaign_type: CampaignType
    start_date: date
    end_date: date
    goal_impressions: int
    ecpm: float
    priority: int
    status: Literal["ACTIVE", "PAUSED", "COMPLETED"] = "ACTIVE"
    targeting: Targeting
    created_at: datetime


class SupplyTag(BaseModel):
    tag_id: str
    tag_name: str
    campaign_id: str
    platform: str
    country: str
    device: str


# --------------------------------------------------------------------------------------
# Data quality
# --------------------------------------------------------------------------------------


class DataQualityCheck(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class DataQualityReport(BaseModel):
    score: float
    verdict: Literal["OK", "DEGRADED", "BAD"]
    checks: list[DataQualityCheck] = []

    @property
    def failed_checks(self) -> list[str]:
        return [c.name for c in self.checks if not c.passed]


# --------------------------------------------------------------------------------------
# The universal normalized record
# --------------------------------------------------------------------------------------


class ScoreComponent(BaseModel):
    label: str
    weight: float
    penalty: float
    points_lost: float


class CampaignHealthRecord(BaseModel):
    campaign_id: str
    line_item_id: str
    campaign_name: str
    advertiser: str
    campaign_type: CampaignType
    ts: datetime

    expected_impressions: int
    actual_impressions: int
    delivery_pct: float
    elapsed_pct: float
    pacing_pct: float
    pacing_gap_pts: float

    fill_rate: float
    baseline_fill_rate: float
    fill_deviation_pct: float
    fill_z_score: float

    error_rate: float
    baseline_error_rate: float
    error_deviation_pct: float
    error_z_score: float

    expected_revenue: float
    actual_revenue: float
    ecpm: float

    eligible_inventory_change_pct: float
    auction_pressure_change_pct: float
    targeting_changed_recently: bool
    creative_error_share: float
    unique_reach_saturation: float
    worst_platform: Optional[str] = None
    worst_vast_code: Optional[str] = None
    vast_error_breakdown: dict[str, int] = {}

    health_score: float
    health_band: HealthBand
    score_components: list[ScoreComponent] = []
    data_quality: DataQualityReport


# --------------------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------------------


class EvidenceItem(BaseModel):
    id: str
    metric: str
    label: str
    current_value: float
    baseline_value: Optional[float] = None
    delta_pct: Optional[float] = None
    z_score: Optional[float] = None
    source: Literal["GAM", "SPRINGSERVE", "ATHENA", "DERIVED"]
    window: str
    strength: Literal["STRONG", "MODERATE", "WEAK"]
    unit: str = ""


class EvidencePackage(BaseModel):
    campaign_id: str
    campaign_name: str
    generated_at: datetime
    window: str
    items: list[EvidenceItem]
    facts: dict[str, Any] = {}


# --------------------------------------------------------------------------------------
# Diagnosis
# --------------------------------------------------------------------------------------


class CandidateCause(BaseModel):
    cause: CauseCode
    label: str
    weight: float
    confidence: float
    evidence_ids: list[str]
    explanation: str = ""


class ConfidenceContribution(BaseModel):
    label: str
    contribution: float


class Diagnosis(BaseModel):
    incident_id: str
    primary_cause: CandidateCause
    secondary_causes: list[CandidateCause] = []
    confidence: float
    confidence_breakdown: list[ConfidenceContribution] = []
    narrative: str
    recommended_action_summary: str = ""
    evidence_used: list[str] = []
    generated_by: str
    model: Optional[str] = None
    generated_at: datetime
    grounding_passed: bool = True
    grounding_notes: list[str] = []
    insufficient_evidence: bool = False


# --------------------------------------------------------------------------------------
# Revenue / recommendation / actions
# --------------------------------------------------------------------------------------


class RevenueRisk(BaseModel):
    impression_gap: int
    ecpm: float
    conservative: float
    expected: float
    worst_case: float
    currency: str = "USD"
    method: str


class Recommendation(BaseModel):
    incident_id: str
    title: str
    action_type: ActionType
    current_state: dict[str, Any]
    proposed_state: dict[str, Any]
    predicted_impression_gain: int
    predicted_recovery: RevenueRisk
    confidence: float
    rationale: str
    requires_approval: bool = True


class TimelineEvent(BaseModel):
    ts: datetime
    label: str
    detail: str = ""
    kind: Literal["signal", "system", "ai", "human", "integration", "impact"] = "system"


class AuditLogEntry(BaseModel):
    ts: datetime
    actor: str
    action: str
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    incident_id: str


class ImpactRecord(BaseModel):
    incident_id: str
    risk_at_detection: float
    risk_timeline: list[dict[str, Any]] = []
    impressions_recovered: int = 0
    revenue_protected: float = 0.0
    time_to_detect_seconds: int = 0
    time_to_resolve_seconds: int = 0
    outcome: Literal["IN_PROGRESS", "RECOVERED", "PARTIAL", "NO_EFFECT"] = "IN_PROGRESS"


class Incident(BaseModel):
    incident_id: str
    campaign_id: str
    campaign_name: str
    advertiser: str
    severity: Severity
    priority: Priority
    status: IncidentStatus = "OPEN"
    detected_at: datetime
    signals: list[str] = []
    health_score: float
    revenue_risk: RevenueRisk
    risk_score: float
    is_data_quality: bool = False
    diagnosis: Optional[Diagnosis] = None
    recommendation: Optional[Recommendation] = None
    timeline: list[TimelineEvent] = []
    audit: list[AuditLogEntry] = []
    impact: Optional[ImpactRecord] = None
    detection_latency_seconds: int = 0
    onset_at: Optional[datetime] = None


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = {}
    duration_ms: int = 0
    ok: bool = True
    result_preview: str = ""


class Envelope(BaseModel):
    data: Any
    meta: dict[str, Any] = Field(default_factory=dict)
