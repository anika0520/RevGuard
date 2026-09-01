"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Activity, ArrowRight, ShieldCheck, TriangleAlert } from "lucide-react";
import Link from "next/link";
import useSWR from "swr";
import { RiskTrendChart } from "@/components/charts/Charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { CountUp } from "@/components/ui/CountUp";
import { EmptyState, Explain, Skeleton } from "@/components/ui/Primitives";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { fetcher } from "@/lib/api";
import { clock, compact, duration, money, moneyFull, pct, severityChip } from "@/lib/format";
import type { Overview, TrendPoint } from "@/lib/types";
import { cn } from "@/lib/utils";

type QueueItem = {
  incident_id: string;
  campaign_id: string;
  campaign_name: string;
  advertiser: string;
  severity: keyof typeof severityChip;
  priority: string;
  status: string;
  revenue_at_risk: number;
  health_score: number;
  primary_cause: string | null;
  confidence: number | null;
  is_data_quality: boolean;
  detected_at: string;
};

const EVENT_STYLE: Record<string, { color: string; label: string }> = {
  "incident.created": { color: "text-danger", label: "INCIDENT" },
  "incident.updated": { color: "text-accent", label: "UPDATE" },
  "action.executed": { color: "text-success", label: "ACTION" },
  "impact.recorded": { color: "text-success", label: "PROTECTED" },
  "analysis.completed": { color: "text-muted", label: "ANALYSIS" },
  "scenario.injected": { color: "text-caution", label: "INJECTED" },
  "simulation.replay": { color: "text-violet-400", label: "REPLAY" },
  "world.reset": { color: "text-muted", label: "RESET" },
  "settings.updated": { color: "text-warning", label: "SETTINGS" },
};

export default function MissionControl() {
  const { data: overview } = useSWR<Overview>("/api/metrics/overview", fetcher, { refreshInterval: 6000 });
  const { data: trend } = useSWR<TrendPoint[]>("/api/metrics/timeseries?days=7", fetcher, { refreshInterval: 15000 });
  const { data: queue } = useSWR<QueueItem[]>("/api/metrics/priority-queue?limit=5", fetcher, { refreshInterval: 6000 });
  const { events, connected } = useLiveEvents();

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-fg">Portfolio overview</h1>
        <p className="mt-1 text-sm text-muted">
          Detect, diagnose, quantify, recommend, act, and measure across every live campaign.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Kpi label="Campaigns monitored" value={overview?.monitored ?? 0} tone="text-fg" />
        <Kpi label="Healthy" value={overview?.healthy ?? 0} tone="text-success" />
        <Kpi label="Warning" value={overview?.warning ?? 0} tone="text-warning" />
        <Kpi label="High risk" value={overview?.high_risk ?? 0} tone="text-caution" />
        <Kpi label="Critical" value={overview?.critical ?? 0} tone="text-danger" pulse />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <HeroCard
          title="Estimated revenue at risk"
          value={overview?.revenue_at_risk ?? 0}
          tone="text-danger"
          accent="from-danger/15"
          icon={<TriangleAlert className="h-4 w-4 text-danger" />}
          footnote={`${overview?.incidents_open ?? 0} open incidents · projected over 7 days or flight end`}
          explain="Sum of the expected revenue at risk across all open incidents. Each incident computes (realized gap + projected gap) / 1000 x eCPM."
        />
        <HeroCard
          title="Revenue protected"
          value={overview?.revenue_protected ?? 0}
          tone="text-success"
          accent="from-success/15"
          icon={<ShieldCheck className="h-4 w-4 text-success" />}
          footnote={`${overview?.incidents_resolved ?? 0} incidents resolved · measured after the fix landed`}
          explain="Risk at detection minus current risk, measured for every incident where a human approved a remediation. Simulated dataset."
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Risk identified vs revenue protected</CardTitle>
            <p className="text-xs text-subtle">Last 7 simulated days</p>
          </CardHeader>
          <CardContent className="pt-2">
            {trend?.length ? <RiskTrendChart data={trend} /> : <Skeleton className="h-52 w-full" />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm">Live signal feed</CardTitle>
            <span className="flex items-center gap-1.5 text-2xs uppercase tracking-wider text-subtle">
              <span className={cn("h-1.5 w-1.5 rounded-full", connected ? "animate-pulse bg-success" : "bg-subtle")} />
              {connected ? "streaming" : "offline"}
            </span>
          </CardHeader>
          <CardContent className="max-h-[248px] overflow-y-auto pt-1">
            {events.length === 0 ? (
              <EmptyState title="Waiting for events" hint="Press Play, or replay the reference incident from the simulation bar." />
            ) : (
              <AnimatePresence initial={false}>
                {events.map((e, i) => {
                  const style = EVENT_STYLE[e.kind] ?? { color: "text-muted", label: e.kind.toUpperCase() };
                  return (
                    <motion.div
                      key={`${e.ts}-${i}`}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-start gap-2 border-b border-line py-1.5 text-xs last:border-0"
                    >
                      <span className="tabular-nums text-subtle">{clock(e.ts)}</span>
                      <span className={cn("font-mono text-2xs font-semibold", style.color)}>{style.label}</span>
                      <span className="min-w-0 flex-1 truncate text-muted">
                        {e.payload.campaign_name ?? e.payload.incident_id ?? e.payload.scenario ?? JSON.stringify(e.payload).slice(0, 60)}
                        {e.payload.revenue_risk ? ` · ${money(e.payload.revenue_risk)}` : ""}
                        {e.payload.revenue_protected ? ` · ${money(e.payload.revenue_protected)} protected` : ""}
                      </span>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader className="flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-sm">Priority queue</CardTitle>
              <p className="text-xs text-subtle">Ranked by business impact, not alert time.</p>
            </div>
            <Link href="/incidents" className="text-xs text-accent hover:underline">
              All incidents →
            </Link>
          </CardHeader>
          <CardContent className="space-y-2 pt-1">
            {!queue ? (
              <Skeleton className="h-40 w-full" />
            ) : queue.length === 0 ? (
              <EmptyState title="No open incidents" hint="Inject a scenario to generate one." />
            ) : (
              queue.map((item) => (
                <Link
                  key={item.incident_id}
                  href={`/campaigns/${item.campaign_id}`}
                  className="group flex items-center gap-3 rounded-xl border border-line bg-elevated px-4 py-3 transition-colors hover:border-line hover:bg-elevated"
                >
                  <span className={cn("rounded-md border px-2 py-1 text-2xs font-bold", severityChip[item.severity])}>
                    {item.priority}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-fg">{item.campaign_name}</p>
                    <p className="truncate text-xs text-subtle">
                      {item.incident_id} · {item.advertiser}
                      {item.is_data_quality ? " · data quality" : item.primary_cause ? ` · ${item.primary_cause}` : " · undiagnosed"}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-danger">{money(item.revenue_at_risk)}</p>
                    <p className="text-2xs text-subtle">health {item.health_score.toFixed(0)}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
                </Link>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4 text-accent" /> System performance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5 pt-1 text-sm">
            <Row
              label="Onset → alert"
              value={duration(overview?.avg_detection_seconds ?? 0)}
              hint={`vs ~${duration(overview?.manual_baseline_seconds ?? 0)} manual baseline`}
              tone="text-success"
              explain="Time from the first degraded window to incident creation, averaged across all incidents."
            />
            <Row
              label="Auto-closed (no action)"
              value={String(overview?.incidents_auto_closed ?? 0)}
              hint="signals stopped agreeing"
              tone="text-fg"
              explain="Incidents the system withdrew on its own when metrics returned inside the expected envelope. This is the false-positive defence working."
            />
            <Row
              label="Data quality"
              value={pct(overview?.data_quality_score ?? 0)}
              hint={`${overview?.data_quality_incidents ?? 0} feed incidents raised`}
              tone="text-accent"
              explain="Mean data-quality score across the portfolio. A BAD verdict raises a DATA_QUALITY incident instead of an underdelivery incident."
            />
            <Row
              label="Analysis runs"
              value={String(overview?.analysis_runs ?? 0)}
              hint="pipeline executions this session"
              tone="text-fg"
              explain="Each run normalizes, quality-checks, scores and anomaly-tests every monitored campaign."
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Kpi({ label, value, tone, pulse }: { label: string; value: number; tone: string; pulse?: boolean }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs uppercase tracking-wider text-subtle">{label}</p>
        <p className={cn("mt-1.5 text-3xl font-semibold tracking-tight", tone, pulse && value > 0 && "animate-pulse")}>
          <CountUp value={value} format={(v) => Math.round(v).toString()} />
        </p>
      </CardContent>
    </Card>
  );
}

function HeroCard({
  title,
  value,
  tone,
  accent,
  icon,
  footnote,
  explain,
}: {
  title: string;
  value: number;
  tone: string;
  accent: string;
  icon: React.ReactNode;
  footnote: string;
  explain: string;
}) {
  return (
    <Card className="overflow-hidden">
      <div className={cn("absolute inset-x-0 top-0 h-24 bg-gradient-to-b to-transparent", accent)} />
      <CardContent className="relative p-5">
        <p className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          {icon} {title} <Explain text={explain} />
        </p>
        <p className={cn("mt-2 text-4xl font-semibold tracking-tight", tone)}>
          <CountUp value={value} format={(v) => moneyFull(v)} />
        </p>
        <p className="mt-1.5 text-xs text-subtle">{footnote}</p>
      </CardContent>
    </Card>
  );
}

function Row({
  label,
  value,
  hint,
  tone,
  explain,
}: {
  label: string;
  value: string;
  hint: string;
  tone: string;
  explain: string;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line pb-2 last:border-0">
      <div>
        <p className="flex items-center gap-1.5 text-xs text-muted">
          {label} <Explain text={explain} />
        </p>
        <p className="text-2xs text-subtle">{hint}</p>
      </div>
      <p className={cn("text-sm font-semibold", tone)}>{value}</p>
    </div>
  );
}
