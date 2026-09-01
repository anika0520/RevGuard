"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR, { mutate } from "swr";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/Card";
import { EmptyState, Skeleton } from "@/components/ui/Primitives";
import { api, fetcher } from "@/lib/api";
import { duration, money, severityChip, signalLabel, stamp, statusChip } from "@/lib/format";
import type { Incident, IncidentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUSES: IncidentStatus[] = [
  "OPEN",
  "INVESTIGATING",
  "AWAITING_APPROVAL",
  "ACTIONED",
  "RESOLVED",
  "FALSE_POSITIVE",
];

export default function IncidentsPage() {
  const [statuses, setStatuses] = useState<IncidentStatus[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const key = useMemo(() => {
    const params = new URLSearchParams({ limit: "300" });
    if (statuses.length) params.set("status", statuses.join(","));
    return `/api/incidents?${params.toString()}`;
  }, [statuses]);

  const { data, isLoading } = useSWR<Incident[]>(key, fetcher, { refreshInterval: 6000 });

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    (data ?? []).forEach((i) => (c[i.status] = (c[i.status] ?? 0) + 1));
    return c;
  }, [data]);

  const diagnoseAll = async () => {
    const targets = (data ?? []).filter((i) => !i.diagnosis && i.status !== "RESOLVED").slice(0, 8);
    if (!targets.length) return toast.info("Nothing left to diagnose");
    setBusy("all");
    try {
      await Promise.all(targets.map((i) => api.diagnose(i.incident_id)));
      mutate(key);
      toast.success(`Diagnosed ${targets.length} incidents`);
    } catch {
      toast.error("Bulk diagnosis failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-fg">Incident Center</h1>
          <p className="mt-1 text-sm text-muted">
            Ranked by risk score = normalized impact × severity × confidence × urgency.
          </p>
        </div>
        <button
          onClick={diagnoseAll}
          disabled={busy !== null}
          className="rounded-lg border border-accent/40 bg-accent/10 px-3 py-2 text-xs font-medium text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
        >
          {busy ? "Diagnosing…" : "Diagnose top 8"}
        </button>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setStatuses((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]))}
            className={cn(
              "rounded-full border px-2.5 py-1 text-xs transition-colors",
              statuses.includes(s) ? statusChip[s] : "border-line text-subtle hover:text-muted"
            )}
          >
            {s.replace("_", " ").toLowerCase()}
            {counts[s] ? <span className="ml-1.5 tabular-nums opacity-70">{counts[s]}</span> : null}
          </button>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !data?.length ? (
            <EmptyState title="No incidents match" hint="Run an analysis or inject a scenario." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface/95 backdrop-blur">
                  <tr className="border-b border-line text-left text-2xs uppercase tracking-wider text-subtle">
                    <th className="px-4 py-3 font-medium">Incident</th>
                    <th className="px-2 py-3 font-medium">Campaign</th>
                    <th className="px-2 py-3 font-medium">Signals</th>
                    <th className="px-2 py-3 font-medium">Root cause</th>
                    <th className="px-2 py-3 font-medium">Status</th>
                    <th className="px-2 py-3 text-right font-medium">Detected</th>
                    <th className="px-4 py-3 text-right font-medium">Risk / protected</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((i) => (
                    <tr key={i.incident_id} className="group border-b border-line transition-colors hover:bg-elevated">
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className={cn("rounded-md border px-1.5 py-0.5 text-2xs font-bold", severityChip[i.severity])}>
                            {i.priority}
                          </span>
                          <span className="font-mono text-xs text-muted">{i.incident_id}</span>
                        </div>
                      </td>
                      <td className="px-2 py-2.5">
                        <Link href={`/campaigns/${i.campaign_id}`} className="block">
                          <p className="font-medium text-fg group-hover:text-accent">{i.campaign_name}</p>
                          <p className="text-xs text-subtle">{i.advertiser}</p>
                        </Link>
                      </td>
                      <td className="px-2 py-2.5">
                        <div className="flex flex-wrap gap-1">
                          {i.signals.slice(0, 3).map((s) => (
                            <span key={s} className="rounded bg-elevated px-1.5 py-0.5 text-2xs text-muted">
                              {signalLabel[s] ?? s}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-2 py-2.5 text-xs">
                        {i.is_data_quality ? (
                          <span className="text-warning">Data quality</span>
                        ) : i.diagnosis ? (
                          <span className="text-muted">
                            {i.diagnosis.primary_cause.label}
                            <span className="ml-1 text-subtle">{(i.diagnosis.confidence * 100).toFixed(0)}%</span>
                          </span>
                        ) : (
                          <span className="text-subtle">undiagnosed</span>
                        )}
                      </td>
                      <td className="px-2 py-2.5">
                        <span className={cn("rounded-full border px-2 py-0.5 text-2xs uppercase tracking-wider", statusChip[i.status])}>
                          {i.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-2 py-2.5 text-right text-xs text-subtle">
                        {stamp(i.detected_at)}
                        <br />
                        <span className="text-subtle">+{duration(i.detection_latency_seconds)} from onset</span>
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <p className="text-sm font-semibold tabular-nums text-danger">{money(i.revenue_risk.expected)}</p>
                        {i.impact?.revenue_protected ? (
                          <p className="text-xs tabular-nums text-success">{money(i.impact.revenue_protected)} protected</p>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
