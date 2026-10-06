"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  BadgeCheck,
  Cpu,
  Loader2,
  MessageSquare,
  ShieldAlert,
  Ticket,
  TrendingDown,
  TriangleAlert,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import useSWR, { mutate } from "swr";
import { toast } from "sonner";
import { PacingChart, RiskBurndown, SignalChart } from "@/components/charts/Charts";
import { CauseWaterfall, ConfidenceRing, HealthGauge } from "@/components/charts/Micro";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { CountUp } from "@/components/ui/CountUp";
import { EmptyState, Explain, Modal, Skeleton, Tabs } from "@/components/ui/Primitives";
import { api, fetcher } from "@/lib/api";
import {
  bandChip,
  bandLabel,
  compact,
  duration,
  money,
  moneyFull,
  num,
  pct,
  signalLabel,
  signedPct,
  sourceChip,
  stamp,
  statusChip,
} from "@/lib/format";
import type { Campaign, EvidencePackage, HealthRecord, Incident, RevenueRisk, SeriesPoint } from "@/lib/types";
import { cn } from "@/lib/utils";

type CampaignPayload = {
  campaign: Campaign;
  health: HealthRecord;
  revenue_risk: RevenueRisk;
  projected_gap: number;
  remaining_hours: number;
  flight_hours: number;
  incident_id: string | null;
};

const PLATFORM_UNIVERSE = ["Roku", "Samsung TV", "LG", "Fire TV", "Web", "Mobile"];
const GEO_UNIVERSE = ["UK", "US", "Canada", "Germany", "Australia"];

export function WarRoom({ campaignId }: { campaignId: string }) {
  const { data, isLoading } = useSWR<CampaignPayload>(`/api/campaigns/${campaignId}`, fetcher, {
    refreshInterval: 6000,
  });
  // One request, one key: the envelope carries both the points and the onset/remediation markers.
  const { data: seriesEnvelope } = useSWR<{ data: SeriesPoint[]; meta: Record<string, any> }>(
    `/api/campaigns/${campaignId}/timeseries?hours=48`,
    async (key: string) => {
      const res = await fetch(key, { cache: "no-store" });
      if (!res.ok) throw new Error("timeseries request failed");
      return res.json();
    },
    { refreshInterval: 8000 }
  );
  const series = seriesEnvelope?.data;
  const seriesMeta = seriesEnvelope?.meta;

  const incidentId = data?.incident_id ?? null;
  const { data: incidentBundle } = useSWR<{ incident: Incident; evidence: EvidencePackage | null }>(
    incidentId ? `/api/incidents/${incidentId}` : null,
    fetcher,
    { refreshInterval: 6000 }
  );

  const [highlight, setHighlight] = useState<string | null>(null);
  const [diagnosing, setDiagnosing] = useState(false);

  const incident = incidentBundle?.incident ?? null;
  const evidence = incidentBundle?.evidence ?? null;
  const diagnosis = incident?.diagnosis ?? null;

  const refresh = useCallback(() => {
    mutate(`/api/campaigns/${campaignId}`);
    if (incidentId) mutate(`/api/incidents/${incidentId}`);
    mutate("/api/metrics/overview");
  }, [campaignId, incidentId]);

  const runDiagnosis = async () => {
    if (!incidentId) return;
    setDiagnosing(true);
    try {
      await api.diagnose(incidentId);
      refresh();
      toast.success("Diagnosis complete — evidence grounded");
    } catch {
      toast.error("Diagnosis failed");
    } finally {
      setDiagnosing(false);
    }
  };

  if (isLoading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-28 w-full" />
        <div className="grid gap-4 lg:grid-cols-3">
          <Skeleton className="h-80 lg:col-span-2" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  const { campaign, health, revenue_risk: risk } = data;
  const onsetAt = seriesMeta?.onset_at ?? null;
  const remediatedAt = seriesMeta?.remediated_at ?? null;

  return (
    <div className="space-y-5">
      <Header campaign={campaign} health={health} incident={incident} data={data} />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        {/* ---------------------------------------------------------------- evidence side */}
        <div className="space-y-5">
          <StatTiles data={data} health={health} risk={risk} />

          <Card>
            <CardHeader className="flex-row items-center justify-between pb-2">
              <div>
                <CardTitle className="text-sm">Delivery vs plan</CardTitle>
                <p className="text-xs text-subtle">
                  Cumulative delivery still reads {pct(health.delivery_pct)} — the collapse is in the rate.
                </p>
              </div>
              <Badge variant="outline" className="text-2xs">48h</Badge>
            </CardHeader>
            <CardContent className="pt-2">
              {series?.length ? (
                <PacingChart data={series} onsetAt={onsetAt} remediatedAt={remediatedAt} />
              ) : (
                <Skeleton className="h-60 w-full" />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Signal panel</CardTitle>
              <p className="text-xs text-subtle">
                Dashed band is the 7-day baseline ±tolerance. Departures are visible without reading a number.
              </p>
            </CardHeader>
            <CardContent className="space-y-4 pt-2">
              <SignalBlock
                title="Fill rate"
                current={pct(health.fill_rate)}
                baseline={pct(health.baseline_fill_rate)}
                delta={health.fill_deviation_pct}
                invert
              >
                {series?.length ? (
                  <SignalChart data={series} dataKey="fill_rate" baseline={health.baseline_fill_rate} color="#38bdf8" onsetAt={onsetAt} />
                ) : null}
              </SignalBlock>
              <SignalBlock
                title="VAST error rate"
                current={pct(health.error_rate, 2)}
                baseline={pct(health.baseline_error_rate, 2)}
                delta={health.error_deviation_pct}
              >
                {series?.length ? (
                  <SignalChart data={series} dataKey="error_rate" baseline={health.baseline_error_rate} color="#f97316" onsetAt={onsetAt} />
                ) : null}
              </SignalBlock>
              <SignalBlock
                title="Eligible inventory"
                current={signedPct(health.eligible_inventory_change_pct)}
                baseline="baseline"
                delta={health.eligible_inventory_change_pct}
                invert
              >
                {series?.length ? (
                  <SignalChart
                    data={series}
                    dataKey="eligible_inventory"
                    baseline={
                      series.slice(0, Math.max(1, series.length - 8)).reduce((a, p) => a + p.eligible_inventory, 0) /
                      Math.max(1, series.length - 8)
                    }
                    color="#a78bfa"
                    unit=""
                    onsetAt={onsetAt}
                  />
                ) : null}
              </SignalBlock>
            </CardContent>
          </Card>

          <EvidenceTable evidence={evidence} highlight={highlight} onHover={setHighlight} />
        </div>

        {/* ---------------------------------------------------------------- AI side */}
        <div className="space-y-5">
          {!incident ? (
            <Card>
              <CardContent className="py-10">
                <EmptyState
                  title="No open incident for this campaign"
                  hint="Signals do not currently agree on a fault. Run an analysis or inject a scenario from the demo bar."
                />
              </CardContent>
            </Card>
          ) : (
            <>
              <DiagnosisCard
                incident={incident}
                diagnosis={diagnosis}
                evidence={evidence}
                onCite={setHighlight}
                onDiagnose={runDiagnosis}
                diagnosing={diagnosing}
              />
              {incident.recommendation ? (
                <RecommendationCard incident={incident} onDone={refresh} />
              ) : null}
              {incident.recommendation?.action_type === "EXPAND_TARGETING" ? (
                <WhatIfSimulator incident={incident} campaign={campaign} />
              ) : null}
              <ImpactPanel incident={incident} />
              <TimelinePanel incident={incident} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------------- header */

function Header({
  campaign,
  health,
  incident,
  data,
}: {
  campaign: Campaign;
  health: HealthRecord;
  incident: Incident | null;
  data: CampaignPayload;
}) {
  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-6 p-6">
        <HealthGauge score={health.health_score} band={health.health_band} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-fg">{campaign.name}</h1>
            <span className={cn("rounded-full border px-2 py-0.5 text-2xs font-semibold uppercase tracking-wider", bandChip[health.health_band])}>
              {bandLabel[health.health_band]}
            </span>
            {incident ? (
              <span className={cn("rounded-full border px-2 py-0.5 text-2xs font-semibold uppercase tracking-wider", statusChip[incident.status])}>
                {incident.incident_id} · {incident.status.replace("_", " ")}
              </span>
            ) : null}
            {health.data_quality.verdict !== "OK" ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-warning/30 bg-warning/10 px-2 py-0.5 text-2xs font-semibold uppercase tracking-wider text-warning">
                <TriangleAlert className="h-3 w-3" /> data {health.data_quality.verdict}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-sm text-muted">
            {campaign.advertiser} · {campaign.campaign_id} · line item {campaign.line_item_id}
          </p>
          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-subtle">
            <span>
              Flight <span className="text-muted">{campaign.start_date} → {campaign.end_date}</span>
            </span>
            <span>
              Goal <span className="text-muted">{compact(campaign.goal_impressions)}</span>
            </span>
            <span>
              eCPM <span className="text-muted">${campaign.ecpm.toFixed(2)}</span>
            </span>
            <span>
              Remaining <span className="text-muted">{duration(data.remaining_hours * 3600)}</span>
            </span>
            <span>
              Targeting{" "}
              <span className="text-muted">
                {[...campaign.targeting.geos, ...campaign.targeting.content_categories, ...campaign.targeting.platforms].join(" + ")}
              </span>
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------------- tiles */

function StatTiles({ data, health, risk }: { data: CampaignPayload; health: HealthRecord; risk: RevenueRisk }) {
  const tiles = [
    {
      label: "Delivery rate vs plan",
      value: pct(health.pacing_pct),
      sub: `${health.pacing_gap_pts >= 0 ? "+" : ""}${health.pacing_gap_pts.toFixed(1)} pts`,
      tone: health.pacing_pct < 85 ? "text-danger" : "text-success",
      explain:
        "Seasonality-adjusted delivery rate over the last 6 hours vs the rate required to hit goal. This is the early-warning signal.",
    },
    {
      label: "Cumulative delivery",
      value: pct(health.delivery_pct),
      sub: `${compact(health.actual_impressions)} of ${compact(health.expected_impressions)}`,
      tone: "text-fg",
      explain: "actual impressions / expected impressions x 100, measured from flight start. Lags the rate signal by hours.",
    },
    {
      label: "Projected shortfall",
      value: compact(data.projected_gap),
      sub: "impressions if rate holds",
      tone: "text-warning",
      explain:
        "required hourly rate x (1 - pacing) x remaining hours, capped at a 7-day horizon or flight end, whichever is sooner.",
    },
    {
      label: "Estimated revenue at risk",
      value: money(risk.expected),
      sub: `${money(risk.conservative)} – ${money(risk.worst_case)}`,
      tone: "text-danger",
      explain: risk.method,
    },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {tiles.map((t) => (
        <Card key={t.label}>
          <CardContent className="p-4">
            <p className="flex items-center gap-1.5 text-xs uppercase tracking-wider text-subtle">
              {t.label} <Explain text={t.explain} />
            </p>
            <p className={cn("mt-2 text-2xl font-semibold tracking-tight", t.tone)}>{t.value}</p>
            <p className="mt-0.5 text-xs text-subtle">{t.sub}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function SignalBlock({
  title,
  current,
  baseline,
  delta,
  invert,
  children,
}: {
  title: string;
  current: string;
  baseline: string;
  delta: number;
  invert?: boolean;
  children: React.ReactNode;
}) {
  const bad = invert ? delta < -8 : delta > 60;
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <p className="text-xs font-medium text-muted">{title}</p>
        <p className="text-xs text-subtle">
          <span className={bad ? "font-semibold text-danger" : "text-fg"}>{current}</span>
          <span className="mx-1.5 text-subtle">vs</span>
          <span>{baseline}</span>
          <span className={cn("ml-2 tabular-nums", bad ? "text-danger" : "text-success")}>{signedPct(delta)}</span>
        </p>
      </div>
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------------- evidence */

function EvidenceTable({
  evidence,
  highlight,
  onHover,
}: {
  evidence: EvidencePackage | null;
  highlight: string | null;
  onHover: (id: string | null) => void;
}) {
  if (!evidence) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Evidence</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState title="Evidence appears once an incident is opened" />
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Evidence package</CardTitle>
        <p className="text-xs text-subtle">
          {evidence.items.length} items · {evidence.window}. Every AI claim cites one of these.
        </p>
      </CardHeader>
      <CardContent className="pt-1">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-line text-left text-2xs uppercase tracking-wider text-subtle">
                <th className="py-2 pr-2 font-medium">ID</th>
                <th className="py-2 pr-2 font-medium">Finding</th>
                <th className="py-2 pr-2 text-right font-medium">Δ%</th>
                <th className="py-2 pr-2 text-right font-medium">z</th>
                <th className="py-2 pr-2 font-medium">Source</th>
                <th className="py-2 font-medium">Strength</th>
              </tr>
            </thead>
            <tbody>
              {evidence.items.map((item) => (
                <tr
                  key={item.id}
                  id={`ev-${item.id}`}
                  onMouseEnter={() => onHover(item.id)}
                  onMouseLeave={() => onHover(null)}
                  className={cn(
                    "border-b border-line transition-colors",
                    highlight === item.id ? "bg-accent/10" : "hover:bg-elevated"
                  )}
                >
                  <td className="py-2 pr-2 font-mono text-2xs text-accent">{item.id}</td>
                  <td className="py-2 pr-2 text-muted">{item.label}</td>
                  <td className="py-2 pr-2 text-right tabular-nums text-muted">
                    {item.delta_pct === null ? "—" : signedPct(item.delta_pct)}
                  </td>
                  <td className="py-2 pr-2 text-right tabular-nums text-muted">
                    {item.z_score === null || item.z_score === 0 ? "—" : item.z_score.toFixed(1)}
                  </td>
                  <td className="py-2 pr-2">
                    <span className={cn("rounded border px-1.5 py-0.5 text-2xs", sourceChip[item.source])}>
                      {item.source}
                    </span>
                  </td>
                  <td className="py-2">
                    <span
                      className={cn(
                        "text-2xs font-semibold uppercase tracking-wider",
                        item.strength === "STRONG"
                          ? "text-success"
                          : item.strength === "MODERATE"
                          ? "text-warning"
                          : "text-subtle"
                      )}
                    >
                      {item.strength}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------------- diagnosis */

function DiagnosisCard({
  incident,
  diagnosis,
  evidence,
  onCite,
  onDiagnose,
  diagnosing,
}: {
  incident: Incident;
  diagnosis: Incident["diagnosis"];
  evidence: EvidencePackage | null;
  onCite: (id: string | null) => void;
  onDiagnose: () => void;
  diagnosing: boolean;
}) {
  const [showConfidence, setShowConfidence] = useState(false);
  const causes = useMemo(
    () => (diagnosis ? [diagnosis.primary_cause, ...diagnosis.secondary_causes] : []),
    [diagnosis]
  );

  const cite = (id: string) => {
    onCite(id);
    document.getElementById(`ev-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => onCite(null), 2200);
  };

  return (
    <Card className={diagnosis ? "" : "border-accent/20"}>
      <CardHeader className="flex-row items-start justify-between pb-3">
        <div>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Cpu className="h-4 w-4 text-accent" /> AI diagnosis
          </CardTitle>
          <p className="mt-1 text-xs text-subtle">
            Deterministic rules rank the causes. The model only writes the explanation.
          </p>
        </div>
        {diagnosis ? <ConfidenceRing value={diagnosis.confidence} /> : null}
      </CardHeader>

      <CardContent className="space-y-4">
        {!diagnosis ? (
          <div className="space-y-3">
            <p className="text-sm text-muted">
              {incident.incident_id} is open with {incident.signals.length} agreeing signals. Run the investigator to
              build an evidence package and synthesize a root cause.
            </p>
            <button
              onClick={onDiagnose}
              disabled={diagnosing}
              className="inline-flex items-center gap-2 rounded-lg bg-accent/15 px-3.5 py-2 text-sm font-medium text-accent transition-colors hover:bg-accent/25 disabled:opacity-50"
            >
              {diagnosing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Activity className="h-4 w-4" />}
              {diagnosing ? "Investigating…" : "Run investigation"}
            </button>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-caution/30 bg-caution/10 px-2.5 py-1 text-xs font-semibold text-caution">
                {diagnosis.primary_cause.label}
              </span>
              {diagnosis.grounding_passed ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-success/30 bg-success/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wider text-success">
                  <BadgeCheck className="h-3 w-3" /> Evidence-grounded
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full border border-danger/30 bg-danger/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wider text-danger">
                  <XCircle className="h-3 w-3" /> Grounding rejected
                </span>
              )}
              <span className="rounded-full border border-line px-2 py-1 text-2xs uppercase tracking-wider text-muted">
                {diagnosis.generated_by === "deterministic" ? "Deterministic engine" : `Model: ${diagnosis.model ?? diagnosis.generated_by}`}
              </span>
              <button
                onClick={() => setShowConfidence(true)}
                className="ml-auto text-2xs uppercase tracking-wider text-subtle underline-offset-2 hover:text-accent hover:underline"
              >
                confidence breakdown
              </button>
            </div>

            <CauseWaterfall causes={causes} />

            <p className="text-sm leading-relaxed text-muted">
              <Citations text={diagnosis.narrative} valid={new Set(evidence?.items.map((i) => i.id) ?? [])} onCite={cite} />
            </p>

            {diagnosis.grounding_notes.length ? (
              <div className="rounded-lg border border-danger/25 bg-danger/5 p-3 text-xs text-danger">
                <p className="font-semibold">Grounding validator rejected the model output:</p>
                <ul className="mt-1 list-disc pl-4">
                  {diagnosis.grounding_notes.map((n, i) => (
                    <li key={i}>{n}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        )}
      </CardContent>

      <Modal
        open={showConfidence}
        onClose={() => setShowConfidence(false)}
        title="How the confidence was computed"
        subtitle="Confidence measures how strongly the available evidence supports the diagnosis — not how sure the model feels."
      >
        <div className="space-y-2">
          {diagnosis?.confidence_breakdown.map((c, i) => (
            <div
              key={i}
              className={cn(
                "flex items-center justify-between rounded-lg px-3 py-2 text-sm",
                i === (diagnosis.confidence_breakdown.length ?? 1) - 1
                  ? "border border-accent/30 bg-accent/10 font-semibold text-accent"
                  : "bg-elevated text-muted"
              )}
            >
              <span className="pr-4">{c.label}</span>
              <span className="tabular-nums">+{c.contribution.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </Modal>
    </Card>
  );
}

/** Renders [EV-xx] markers as clickable chips that jump to the source signal. */
function Citations({
  text,
  valid,
  onCite,
}: {
  text: string;
  valid: Set<string>;
  onCite: (id: string) => void;
}) {
  const parts = text.split(/(\[EV-\d{2}\])/g);
  return (
    <>
      {parts.map((part, i) => {
        const match = part.match(/^\[(EV-\d{2})\]$/);
        if (!match) return <span key={i}>{part}</span>;
        const id = match[1];
        const known = valid.has(id);
        return (
          <button
            key={i}
            onClick={() => known && onCite(id)}
            className={cn(
              "mx-0.5 rounded border px-1 py-px font-mono text-2xs align-middle transition-colors",
              known
                ? "border-accent/30 bg-accent/10 text-accent hover:bg-accent/25"
                : "border-danger/40 bg-danger/10 text-danger"
            )}
            title={known ? "Jump to the source signal" : "Unknown citation — would be rejected"}
          >
            {id}
          </button>
        );
      })}
    </>
  );
}

/* ------------------------------------------------------------------------- recommendation */

function RecommendationCard({ incident, onDone }: { incident: Incident; onDone: () => void }) {
  const r = incident.recommendation!;
  const [preview, setPreview] = useState<null | "slack" | "jira">(null);
  const [payload, setPayload] = useState<any>(null);
  const [tab, setTab] = useState("Preview");
  const [busy, setBusy] = useState(false);

  const openPreview = async (kind: "slack" | "jira") => {
    setBusy(true);
    try {
      setPayload(kind === "slack" ? await api.slackPreview(incident.incident_id) : await api.jiraPreview(incident.incident_id));
      setTab("Preview");
      setPreview(kind);
    } catch {
      toast.error("Could not build the payload");
    } finally {
      setBusy(false);
    }
  };

  const act = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      setPreview(null);
      onDone();
      toast.success(label);
    } catch {
      toast.error(`${label} failed`);
    } finally {
      setBusy(false);
    }
  };

  const done = incident.status === "ACTIONED" || incident.status === "RESOLVED";

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <ShieldAlert className="h-4 w-4 text-success" /> Recommended action
        </CardTitle>
        <p className="mt-1 text-xs text-subtle">Human approval required. Nothing is applied automatically.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm font-medium text-fg">{r.title}</p>

        <div className="grid gap-2 text-xs sm:grid-cols-2">
          <div className="rounded-lg border border-danger/20 bg-danger/[0.06] p-3">
            <p className="mb-1 text-2xs uppercase tracking-wider text-danger">Current</p>
            <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-muted line-through decoration-danger/50">
              {JSON.stringify(r.current_state, null, 1)}
            </pre>
          </div>
          <div className="rounded-lg border border-success/20 bg-success/[0.06] p-3">
            <p className="mb-1 text-2xs uppercase tracking-wider text-success">Proposed</p>
            <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-success">
              {JSON.stringify(r.proposed_state, null, 1)}
            </pre>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 rounded-lg border border-line bg-elevated p-3 text-center">
          <div>
            <p className="text-2xs uppercase tracking-wider text-subtle">Predicted gain</p>
            <p className="mt-1 text-base font-semibold text-success">+{compact(r.predicted_impression_gain)}</p>
          </div>
          <div>
            <p className="flex items-center justify-center gap-1 text-2xs uppercase tracking-wider text-subtle">
              Recovery <Explain text={r.predicted_recovery.method} />
            </p>
            <p className="mt-1 text-base font-semibold text-success">
              {money(r.predicted_recovery.conservative)}–{money(r.predicted_recovery.worst_case)}
            </p>
          </div>
          <div>
            <p className="text-2xs uppercase tracking-wider text-subtle">Confidence</p>
            <p className="mt-1 text-base font-semibold text-accent">{(r.confidence * 100).toFixed(0)}%</p>
          </div>
        </div>

        <p className="text-xs leading-relaxed text-muted">{r.rationale}</p>

        <div className="flex flex-wrap gap-2">
          <button
            disabled={busy || done}
            onClick={() => act("Approved — remediation applied to the simulated world", () => api.approve(incident.incident_id))}
            className="inline-flex items-center gap-2 rounded-lg bg-success/15 px-3.5 py-2 text-sm font-medium text-success transition-colors hover:bg-success/25 disabled:opacity-40"
          >
            <BadgeCheck className="h-4 w-4" /> {done ? "Approved" : "Approve & simulate fix"}
          </button>
          <button
            disabled={busy}
            onClick={() => openPreview("jira")}
            className="inline-flex items-center gap-2 rounded-lg border border-line px-3.5 py-2 text-sm text-muted transition-colors hover:bg-elevated"
          >
            <Ticket className="h-4 w-4" /> Create JIRA
          </button>
          <button
            disabled={busy}
            onClick={() => openPreview("slack")}
            className="inline-flex items-center gap-2 rounded-lg border border-line px-3.5 py-2 text-sm text-muted transition-colors hover:bg-elevated"
          >
            <MessageSquare className="h-4 w-4" /> Send to Slack
          </button>
          <button
            disabled={busy || done}
            onClick={() => act("Marked as a false positive", () => api.falsePositive(incident.incident_id))}
            className="inline-flex items-center gap-2 rounded-lg border border-line px-3.5 py-2 text-sm text-muted transition-colors hover:bg-elevated"
          >
            <XCircle className="h-4 w-4" /> False positive
          </button>
        </div>
      </CardContent>

      <Modal
        open={preview !== null}
        onClose={() => setPreview(null)}
        wide
        title={preview === "slack" ? "Slack alert" : `JIRA issue`}
        subtitle="DRY_RUN is on — this is the exact payload that would be sent. Flip to Payload to inspect it."
        footer={
          <>
            <button onClick={() => setPreview(null)} className="rounded-lg border border-line px-3 py-1.5 text-sm text-muted">
              Close
            </button>
            <button
              disabled={busy}
              onClick={() =>
                preview === "slack"
                  ? act("Slack alert dispatched", () => api.slackSend(incident.incident_id))
                  : act("JIRA ticket created", () => api.jiraCreate(incident.incident_id))
              }
              className="rounded-lg bg-success/15 px-3 py-1.5 text-sm font-medium text-success hover:bg-success/25"
            >
              {preview === "slack" ? "Send" : "Create ticket"}
            </button>
          </>
        }
      >
        <div className="mb-3">
          <Tabs tabs={["Preview", "Payload"]} active={tab} onChange={setTab} />
        </div>
        {tab === "Payload" ? (
          <pre className="max-h-[50vh] overflow-auto rounded-lg border border-line bg-elevated p-4 font-mono text-xs leading-relaxed text-muted">
            {JSON.stringify(payload, null, 2)}
          </pre>
        ) : preview === "slack" ? (
          <SlackPreview payload={payload} />
        ) : (
          <JiraPreview payload={payload} incident={incident} />
        )}
      </Modal>
    </Card>
  );
}

function SlackPreview({ payload }: { payload: any }) {
  return (
    <div className="rounded-lg border border-line bg-elevated p-4">
      <div className="flex gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-accent text-xs font-semibold text-white">RG</div>
        <div className="min-w-0 flex-1 space-y-2 text-sm">
          <p className="font-semibold text-fg">
            RevGuard <span className="ml-1 rounded bg-elevated px-1 py-px text-2xs uppercase text-muted">APP</span>
          </p>
          {payload?.blocks?.map((b: any, i: number) => {
            if (b.type === "header") return <p key={i} className="text-base font-bold text-fg">{b.text.text}</p>;
            if (b.type === "section")
              return (
                <div key={i} className="space-y-1 whitespace-pre-wrap text-muted">
                  <p>{b.text?.text?.replace(/\*/g, "")}</p>
                  {b.fields?.map((f: any, j: number) => (
                    <p key={j} className="text-muted">{f.text.replace(/\*/g, "")}</p>
                  ))}
                </div>
              );
            if (b.type === "actions")
              return (
                <div key={i} className="flex gap-2 pt-1">
                  {b.elements.map((e: any, j: number) => (
                    <span key={j} className={cn("rounded border px-3 py-1 text-xs", j === 0 ? "border-success bg-success/80 text-white" : "border-line text-muted")}>
                      {e.text.text}
                    </span>
                  ))}
                </div>
              );
            if (b.type === "context")
              return <p key={i} className="pt-1 text-xs text-subtle">{b.elements[0].text}</p>;
            return null;
          })}
        </div>
      </div>
    </div>
  );
}

function JiraPreview({ payload, incident }: { payload: any; incident: Incident }) {
  const f = payload?.fields;
  const flatten = (content: any[]): React.ReactNode[] =>
    content.map((node, i) => {
      if (node.type === "heading")
        return <p key={i} className="mt-3 text-xs font-semibold uppercase tracking-wider text-muted">{node.content[0].text}</p>;
      if (node.type === "paragraph")
        return <p key={i} className="mt-1.5 text-sm leading-relaxed text-muted">{node.content?.[0]?.text}</p>;
      if (node.type === "bulletList")
        return (
          <ul key={i} className="mt-1.5 list-disc space-y-0.5 pl-5 text-sm text-muted">
            {node.content.map((li: any, j: number) => (
              <li key={j}>{li.content[0].content[0].text}</li>
            ))}
          </ul>
        );
      return null;
    });
  return (
    <div className="rounded-lg border border-line bg-elevated p-4">
      <div className="flex items-center gap-2 text-xs text-subtle">
        <span className="rounded bg-accent/15 px-1.5 py-0.5 font-mono text-accent">
          {f?.project?.key}-{incident.incident_id.split("-").at(-1)}
        </span>
        <span>Bug</span>
        <span>·</span>
        <span className="text-danger">{f?.priority?.name}</span>
      </div>
      <h4 className="mt-2 text-base font-semibold text-fg">{f?.summary}</h4>
      <div className="mt-1 flex flex-wrap gap-1">
        {f?.labels?.map((l: string) => (
          <span key={l} className="rounded bg-elevated px-1.5 py-0.5 text-2xs text-muted">{l}</span>
        ))}
      </div>
      <div className="mt-3 border-t border-line pt-2">{f ? flatten(f.description.content) : null}</div>
    </div>
  );
}

/* ------------------------------------------------------------------------- what-if */

function WhatIfSimulator({ incident, campaign }: { incident: Incident; campaign: Campaign }) {
  const [platforms, setPlatforms] = useState<string[]>(campaign.targeting.platforms);
  const [geos, setGeos] = useState<string[]>(campaign.targeting.geos);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const toggle = (list: string[], setList: (v: string[]) => void, value: string) =>
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);

  const evaluate = async (nextPlatforms = platforms, nextGeos = geos) => {
    setBusy(true);
    try {
      setResult(await api.whatIf(incident.incident_id, { platforms: nextPlatforms, geos: nextGeos }));
    } catch {
      toast.error("What-if evaluation failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <TrendingDown className="h-4 w-4 text-violet-400" /> What-if simulator
        </CardTitle>
        <p className="mt-1 text-xs text-subtle">
          Toggle a restriction and the backend re-scores the recoverable shortfall live.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <Toggles label="Platforms" universe={PLATFORM_UNIVERSE} selected={platforms} onToggle={(v) => {
          const next = platforms.includes(v) ? platforms.filter((p) => p !== v) : [...platforms, v];
          setPlatforms(next);
          evaluate(next, geos);
        }} />
        <Toggles label="Geographies" universe={GEO_UNIVERSE} selected={geos} onToggle={(v) => {
          const next = geos.includes(v) ? geos.filter((g) => g !== v) : [...geos, v];
          setGeos(next);
          evaluate(platforms, next);
        }} />

        <AnimatePresence mode="wait">
          {result ? (
            <motion.div
              key={result.inventory_effect_pct}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-3 gap-3 rounded-lg border border-violet-500/20 bg-violet-500/[0.06] p-3 text-center"
            >
              <div>
                <p className="text-2xs uppercase tracking-wider text-subtle">Inventory effect</p>
                <p className="mt-1 text-base font-semibold text-violet-300">{signedPct(result.inventory_effect_pct)}</p>
              </div>
              <div>
                <p className="text-2xs uppercase tracking-wider text-subtle">Impressions</p>
                <p className="mt-1 text-base font-semibold text-success">
                  +<CountUp value={result.predicted_impression_gain} format={compact} />
                </p>
              </div>
              <div>
                <p className="text-2xs uppercase tracking-wider text-subtle">Recovery</p>
                <p className="mt-1 text-base font-semibold text-success">
                  <CountUp value={result.predicted_recovery.expected} format={(v) => money(v)} />
                </p>
              </div>
            </motion.div>
          ) : (
            <p className="text-xs text-subtle">{busy ? "Evaluating…" : "Toggle a dimension to model the impact."}</p>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}

function Toggles({
  label,
  universe,
  selected,
  onToggle,
}: {
  label: string;
  universe: string[];
  selected: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <div>
      <p className="mb-1.5 text-2xs uppercase tracking-wider text-subtle">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {universe.map((v) => {
          const on = selected.includes(v);
          return (
            <button
              key={v}
              onClick={() => onToggle(v)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs transition-colors",
                on
                  ? "border-success/40 bg-success/15 text-success"
                  : "border-line text-subtle hover:border-line hover:text-muted"
              )}
            >
              {v}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------------- impact + timeline */

function ImpactPanel({ incident }: { incident: Incident }) {
  const impact = incident.impact;
  if (!impact || impact.risk_timeline.length < 2) return null;
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm">Risk burn-down</CardTitle>
        {impact.revenue_protected > 0 ? (
          <span className="rounded-full border border-success/30 bg-success/10 px-2.5 py-1 text-xs font-semibold text-success">
            {moneyFull(impact.revenue_protected)} protected
          </span>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-3 pt-1">
        <RiskBurndown points={impact.risk_timeline} />
        <div className="grid grid-cols-3 gap-3 text-center text-xs">
          <Stat label="Impressions recovered" value={compact(impact.impressions_recovered)} />
          <Stat label="Onset → alert" value={duration(impact.time_to_detect_seconds)} />
          <Stat label="Outcome" value={impact.outcome.replace("_", " ")} />
        </div>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-elevated p-2.5">
      <p className="text-2xs uppercase tracking-wider text-subtle">{label}</p>
      <p className="mt-1 text-sm font-semibold text-fg">{value}</p>
    </div>
  );
}

const KIND_COLOR: Record<string, string> = {
  signal: "bg-caution",
  system: "bg-accent",
  ai: "bg-violet-400",
  human: "bg-success",
  integration: "bg-warning",
  impact: "bg-success",
};

function TimelinePanel({ incident }: { incident: Incident }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Incident timeline</CardTitle>
        <p className="text-xs text-subtle">
          {incident.signals.map((s) => signalLabel[s] ?? s).join(" · ")}
        </p>
      </CardHeader>
      <CardContent className="pt-1">
        <ol className="relative space-y-3 border-l border-line pl-4">
          {incident.timeline.map((e, i) => (
            <li key={i} className="relative">
              <span className={cn("absolute -left-[21px] top-1.5 h-2 w-2 rounded-full", KIND_COLOR[e.kind] ?? "bg-subtle")} />
              <p className="text-xs font-medium text-fg">{e.label}</p>
              {e.detail ? <p className="text-xs leading-relaxed text-subtle">{e.detail}</p> : null}
              <p className="mt-0.5 text-2xs tabular-nums text-subtle">{stamp(e.ts)}</p>
            </li>
          ))}
        </ol>
        {incident.audit.length ? (
          <div className="mt-4 border-t border-line pt-3">
            <p className="mb-2 text-2xs uppercase tracking-wider text-subtle">Audit log</p>
            {incident.audit.map((a, i) => (
              <p key={i} className="font-mono text-2xs text-subtle">
                {stamp(a.ts)} · {a.actor} · {a.action}
              </p>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
