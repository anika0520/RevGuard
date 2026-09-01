"use client";

import useSWR from "swr";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { CountUp } from "@/components/ui/CountUp";
import { EmptyState, Explain, Skeleton } from "@/components/ui/Primitives";
import { fetcher } from "@/lib/api";
import { compact, duration, money, moneyFull, pct, severityChip, stamp } from "@/lib/format";
import type { ImpactLedger } from "@/lib/types";
import { cn } from "@/lib/utils";

const OUTCOME_TONE: Record<string, string> = {
  RECOVERED: "text-success",
  PARTIAL: "text-warning",
  NO_EFFECT: "text-danger",
  IN_PROGRESS: "text-accent",
};

export default function ImpactPage() {
  const { data, isLoading } = useSWR<ImpactLedger>("/api/impact", fetcher, { refreshInterval: 8000 });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-fg">Impact ledger</h1>
        <p className="mt-1 text-sm text-muted">
          The measurement step most monitoring stops short of: did the intervention actually recover the money?
        </p>
      </div>

      {isLoading || !data ? (
        <Skeleton className="h-32 w-full" />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Tile
              label="Revenue protected"
              value={<CountUp value={data.total_protected} format={moneyFull} />}
              tone="text-success"
              explain="Risk at detection minus risk after the approved remediation, summed across resolved incidents."
            />
            <Tile
              label="Identified at risk"
              value={<CountUp value={data.total_identified} format={moneyFull} />}
              tone="text-danger"
              explain="Sum of the estimated revenue at risk at the moment each incident was created."
            />
            <Tile label="Recovery rate" value={pct(data.recovery_rate)} tone="text-accent" explain="protected / identified x 100." />
            <Tile label="Onset → alert" value={duration(data.avg_detect_seconds)} tone="text-fg" explain="Mean time from the first degraded window to incident creation." />
            <Tile label="Alert → resolved" value={duration(data.avg_resolve_seconds)} tone="text-fg" explain="Mean time from incident creation to the risk burning down to zero." />
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)]">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Ledger</CardTitle>
                <p className="text-xs text-subtle">{data.rows.length} incidents with measured impact · simulated dataset</p>
              </CardHeader>
              <CardContent className="p-0">
                {!data.rows.length ? (
                  <EmptyState title="No measured impact yet" hint="Approve a recommendation and advance the clock." />
                ) : (
                  <div className="max-h-[520px] overflow-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-surface/95 backdrop-blur">
                        <tr className="border-b border-line text-left text-2xs uppercase tracking-wider text-subtle">
                          <th className="px-4 py-3 font-medium">Incident</th>
                          <th className="px-2 py-3 font-medium">Campaign</th>
                          <th className="px-2 py-3 text-right font-medium">At risk</th>
                          <th className="px-2 py-3 text-right font-medium">Protected</th>
                          <th className="px-2 py-3 text-right font-medium">Impressions</th>
                          <th className="px-2 py-3 text-right font-medium">MTTR</th>
                          <th className="px-4 py-3 font-medium">Outcome</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.rows.map((r) => (
                          <tr key={r.incident_id} className="border-b border-line hover:bg-elevated">
                            <td className="px-4 py-2.5">
                              <span className="font-mono text-xs text-muted">{r.incident_id}</span>
                              <p className="text-2xs text-subtle">{stamp(r.detected_at)}</p>
                            </td>
                            <td className="px-2 py-2.5">
                              <p className="text-fg">{r.campaign_name}</p>
                              <span className={cn("rounded border px-1.5 py-0.5 text-2xs font-semibold", severityChip[r.severity])}>
                                {r.severity}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 text-right tabular-nums text-danger">{money(r.risk_at_detection)}</td>
                            <td className="px-2 py-2.5 text-right font-semibold tabular-nums text-success">
                              {money(r.revenue_protected)}
                            </td>
                            <td className="px-2 py-2.5 text-right tabular-nums text-muted">
                              {compact(r.impressions_recovered)}
                            </td>
                            <td className="px-2 py-2.5 text-right tabular-nums text-muted">
                              {duration(r.time_to_resolve_seconds)}
                            </td>
                            <td className={cn("px-4 py-2.5 text-xs font-medium", OUTCOME_TONE[r.outcome])}>
                              {r.outcome.replace("_", " ")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Outcomes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 pt-1">
                {Object.entries(data.outcomes).map(([outcome, count]) => {
                  const total = Object.values(data.outcomes).reduce((a, b) => a + b, 0) || 1;
                  return (
                    <div key={outcome}>
                      <div className="mb-1 flex justify-between text-xs">
                        <span className={OUTCOME_TONE[outcome]}>{outcome.replace("_", " ")}</span>
                        <span className="tabular-nums text-muted">{count}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-elevated">
                        <div
                          className={cn(
                            "h-full rounded-full",
                            outcome === "RECOVERED" ? "bg-success" : outcome === "PARTIAL" ? "bg-warning" : "bg-subtle"
                          )}
                          style={{ width: `${(count / total) * 100}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
                <div className="mt-4 rounded-lg border border-success/20 bg-success/[0.06] p-3 text-xs leading-relaxed text-success/80">
                  Across this dataset, RevGuard identified {moneyFull(data.total_identified)} of revenue at risk and
                  protected an estimated {moneyFull(data.total_protected)} — with a mean onset-to-alert of{" "}
                  {duration(data.avg_detect_seconds)} against a manual baseline measured in days.
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function Tile({
  label,
  value,
  tone,
  explain,
}: {
  label: string;
  value: React.ReactNode;
  tone: string;
  explain: string;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="flex items-center gap-1.5 text-xs uppercase tracking-wider text-subtle">
          {label} <Explain text={explain} />
        </p>
        <p className={cn("mt-1.5 text-2xl font-semibold tracking-tight", tone)}>{value}</p>
      </CardContent>
    </Card>
  );
}
