export type HealthBand = "HEALTHY" | "WARNING" | "HIGH_RISK" | "CRITICAL";
export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type Priority = "P0" | "P1" | "P2" | "P3";
export type IncidentStatus =
  | "OPEN"
  | "INVESTIGATING"
  | "AWAITING_APPROVAL"
  | "ACTIONED"
  | "RESOLVED"
  | "FALSE_POSITIVE";

export interface Envelope<T> {
  data: T;
  meta: Record<string, any>;
}

export interface Overview {
  monitored: number;
  healthy: number;
  warning: number;
  high_risk: number;
  critical: number;
  revenue_at_risk: number;
  revenue_protected: number;
  incidents_open: number;
  incidents_resolved: number;
  incidents_auto_closed: number;
  avg_detection_seconds: number;
  manual_baseline_seconds: number;
  data_quality_score: number;
  data_quality_incidents: number;
  analysis_runs: number;
}

export interface TrendPoint {
  date: string;
  at_risk: number;
  protected: number;
  incidents: number;
}

export interface CampaignRow {
  campaign_id: string;
  campaign_name: string;
  advertiser: string;
  campaign_type: string;
  health_score: number;
  health_band: HealthBand;
  pacing_pct: number;
  delivery_pct: number;
  fill_rate: number;
  baseline_fill_rate: number;
  error_rate: number;
  baseline_error_rate: number;
  expected_impressions: number;
  actual_impressions: number;
  revenue_at_risk: number;
  goal_impressions: number;
  ecpm: number;
  geos: string[];
  platforms: string[];
  end_date: string;
  remaining_hours: number;
  data_quality: "OK" | "DEGRADED" | "BAD";
}

export interface ScoreComponent {
  label: string;
  weight: number;
  penalty: number;
  points_lost: number;
}

export interface DataQualityCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface HealthRecord {
  campaign_id: string;
  campaign_name: string;
  advertiser: string;
  campaign_type: string;
  ts: string;
  expected_impressions: number;
  actual_impressions: number;
  delivery_pct: number;
  elapsed_pct: number;
  pacing_pct: number;
  pacing_gap_pts: number;
  fill_rate: number;
  baseline_fill_rate: number;
  fill_deviation_pct: number;
  fill_z_score: number;
  error_rate: number;
  baseline_error_rate: number;
  error_deviation_pct: number;
  error_z_score: number;
  expected_revenue: number;
  actual_revenue: number;
  ecpm: number;
  eligible_inventory_change_pct: number;
  auction_pressure_change_pct: number;
  targeting_changed_recently: boolean;
  creative_error_share: number;
  unique_reach_saturation: number;
  worst_platform: string | null;
  worst_vast_code: string | null;
  vast_error_breakdown: Record<string, number>;
  health_score: number;
  health_band: HealthBand;
  score_components: ScoreComponent[];
  data_quality: { score: number; verdict: "OK" | "DEGRADED" | "BAD"; checks: DataQualityCheck[] };
}

export interface Targeting {
  geos: string[];
  devices: string[];
  platforms: string[];
  content_categories: string[];
  frequency_cap: number | null;
  last_changed_at: string | null;
}

export interface Campaign {
  campaign_id: string;
  line_item_id: string;
  name: string;
  advertiser: string;
  campaign_type: string;
  start_date: string;
  end_date: string;
  goal_impressions: number;
  ecpm: number;
  priority: number;
  status: string;
  targeting: Targeting;
}

export interface RevenueRisk {
  impression_gap: number;
  ecpm: number;
  conservative: number;
  expected: number;
  worst_case: number;
  currency: string;
  method: string;
}

export interface EvidenceItem {
  id: string;
  metric: string;
  label: string;
  current_value: number;
  baseline_value: number | null;
  delta_pct: number | null;
  z_score: number | null;
  source: "GAM" | "SPRINGSERVE" | "ATHENA" | "DERIVED";
  window: string;
  strength: "STRONG" | "MODERATE" | "WEAK";
  unit: string;
}

export interface EvidencePackage {
  campaign_id: string;
  campaign_name: string;
  generated_at: string;
  window: string;
  items: EvidenceItem[];
  facts: Record<string, any>;
}

export interface CandidateCause {
  cause: string;
  label: string;
  weight: number;
  confidence: number;
  evidence_ids: string[];
  explanation: string;
}

export interface Diagnosis {
  incident_id: string;
  primary_cause: CandidateCause;
  secondary_causes: CandidateCause[];
  confidence: number;
  confidence_breakdown: { label: string; contribution: number }[];
  narrative: string;
  recommended_action_summary: string;
  evidence_used: string[];
  generated_by: string;
  model: string | null;
  generated_at: string;
  grounding_passed: boolean;
  grounding_notes: string[];
  insufficient_evidence: boolean;
}

export interface Recommendation {
  incident_id: string;
  title: string;
  action_type: string;
  current_state: Record<string, any>;
  proposed_state: Record<string, any>;
  predicted_impression_gain: number;
  predicted_recovery: RevenueRisk;
  confidence: number;
  rationale: string;
  requires_approval: boolean;
}

export interface TimelineEvent {
  ts: string;
  label: string;
  detail: string;
  kind: "signal" | "system" | "ai" | "human" | "integration" | "impact";
}

export interface ImpactRecord {
  incident_id: string;
  risk_at_detection: number;
  risk_timeline: { ts: string; risk: number }[];
  impressions_recovered: number;
  revenue_protected: number;
  time_to_detect_seconds: number;
  time_to_resolve_seconds: number;
  outcome: "IN_PROGRESS" | "RECOVERED" | "PARTIAL" | "NO_EFFECT";
}

export interface Incident {
  incident_id: string;
  campaign_id: string;
  campaign_name: string;
  advertiser: string;
  severity: Severity;
  priority: Priority;
  status: IncidentStatus;
  detected_at: string;
  signals: string[];
  health_score: number;
  revenue_risk: RevenueRisk;
  risk_score: number;
  is_data_quality: boolean;
  diagnosis: Diagnosis | null;
  recommendation: Recommendation | null;
  timeline: TimelineEvent[];
  audit: { ts: string; actor: string; action: string; before: any; after: any }[];
  impact: ImpactRecord | null;
  detection_latency_seconds: number;
  onset_at: string | null;
}

export interface ToolCall {
  name: string;
  arguments: Record<string, any>;
  duration_ms: number;
  ok: boolean;
  result_preview: string;
}

export interface SeriesPoint {
  ts: string;
  impressions: number;
  expected_impressions: number;
  cumulative_impressions: number;
  cumulative_expected: number;
  fill_rate: number;
  error_rate: number;
  eligible_inventory: number;
  revenue: number;
  valid: boolean;
}

export interface SimState {
  sim_clock: string;
  speed: number;
  running: boolean;
  world_start: string;
  world_end: string;
  golden_campaign_id: string;
  analysis_runs: number;
}

export interface GuardianEvent {
  kind: string;
  ts: string;
  payload: Record<string, any>;
}

export interface ImpactLedger {
  rows: {
    incident_id: string;
    campaign_name: string;
    advertiser: string;
    severity: Severity;
    detected_at: string;
    risk_at_detection: number;
    revenue_protected: number;
    impressions_recovered: number;
    time_to_detect_seconds: number;
    time_to_resolve_seconds: number;
    outcome: string;
  }[];
  total_protected: number;
  total_identified: number;
  recovery_rate: number;
  outcomes: Record<string, number>;
  avg_detect_seconds: number;
  avg_resolve_seconds: number;
}
