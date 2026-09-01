"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { HealthGauge, PacingBar, Sparkline } from "@/components/charts/Micro";
import { Card, CardContent } from "@/components/ui/Card";
import { EmptyState, Skeleton } from "@/components/ui/Primitives";
import { fetcher } from "@/lib/api";
import { bandChip, bandLabel, compact, money, pct, signedPct } from "@/lib/format";
import type { CampaignRow, HealthBand } from "@/lib/types";
import { cn } from "@/lib/utils";

const BANDS: HealthBand[] = ["CRITICAL", "HIGH_RISK", "WARNING", "HEALTHY"];
const SORTS = [
  { id: "risk", label: "Revenue at risk" },
  { id: "health", label: "Health score" },
  { id: "pacing", label: "Pacing" },
  { id: "fill", label: "Fill rate" },
  { id: "errors", label: "VAST errors" },
  { id: "name", label: "Name" },
];

export default function CampaignsPage() {
  const [q, setQ] = useState("");
  const [bands, setBands] = useState<HealthBand[]>([]);
  const [sort, setSort] = useState("risk");

  const key = useMemo(() => {
    const params = new URLSearchParams({ sort, limit: "250" });
    if (q) params.set("q", q);
    if (bands.length) params.set("band", bands.join(","));
    return `/api/campaigns?${params.toString()}`;
  }, [q, bands, sort]);

  const { data, isLoading } = useSWR<CampaignRow[]>(key, fetcher, { refreshInterval: 10000 });

  const toggleBand = (b: HealthBand) =>
    setBands((prev) => (prev.includes(b) ? prev.filter((x) => x !== b) : [...prev, b]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-fg">Campaign Health</h1>
          <p className="mt-1 text-sm text-muted">
            Every campaign, scored by the same deterministic engine. Click any row to open the war room.
          </p>
        </div>
        <p className="text-xs text-subtle">
          <span className="tabular-nums text-muted">{data?.length ?? 0}</span> shown
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search campaign, advertiser or id…"
          className="w-72 rounded-lg border border-line bg-elevated px-3 py-2 text-sm text-fg outline-none placeholder:text-subtle focus:border-accent/40"
        />
        <div className="flex gap-1.5">
          {BANDS.map((b) => (
            <button
              key={b}
              onClick={() => toggleBand(b)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs transition-colors",
                bands.includes(b) ? bandChip[b] : "border-line text-subtle hover:text-muted"
              )}
            >
              {bandLabel[b]}
            </button>
          ))}
        </div>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="ml-auto rounded-lg border border-line bg-surface px-3 py-2 text-xs text-muted outline-none"
        >
          {SORTS.map((s) => (
            <option key={s.id} value={s.id}>
              Sort: {s.label}
            </option>
          ))}
        </select>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-11 w-full" />
              ))}
            </div>
          ) : !data?.length ? (
            <EmptyState title="No campaigns match those filters" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface/95 backdrop-blur">
                  <tr className="border-b border-line text-left text-2xs uppercase tracking-wider text-subtle">
                    <th className="px-4 py-3 font-medium">Health</th>
                    <th className="px-2 py-3 font-medium">Campaign</th>
                    <th className="px-2 py-3 font-medium">Delivery rate</th>
                    <th className="px-2 py-3 font-medium">Fill</th>
                    <th className="px-2 py-3 font-medium">VAST errors</th>
                    <th className="px-2 py-3 text-right font-medium">Delivered</th>
                    <th className="px-4 py-3 text-right font-medium">At risk</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((c) => (
                    <tr key={c.campaign_id} className="group border-b border-line transition-colors hover:bg-elevated">
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <HealthGauge score={c.health_score} band={c.health_band} size={34} stroke={4} />
                          {c.data_quality !== "OK" ? (
                            <span className="rounded border border-warning/30 bg-warning/10 px-1 py-0.5 text-2xs font-semibold uppercase text-warning">
                              feed
                            </span>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-2 py-2.5">
                        <Link href={`/campaigns/${c.campaign_id}`} className="block">
                          <p className="font-medium text-fg group-hover:text-accent">{c.campaign_name}</p>
                          <p className="text-xs text-subtle">
                            {c.advertiser} · {c.campaign_id} · {c.platforms.join(", ")}
                          </p>
                        </Link>
                      </td>
                      <td className="px-2 py-2.5">
                        <PacingBar value={c.pacing_pct} />
                      </td>
                      <td className="px-2 py-2.5">
                        <div className="flex items-center gap-2">
                          <Sparkline
                            values={[c.baseline_fill_rate, c.baseline_fill_rate, c.fill_rate, c.fill_rate]}
                            color={c.fill_rate < c.baseline_fill_rate * 0.85 ? "#ef4444" : "#38bdf8"}
                            width={44}
                            height={18}
                          />
                          <span className={cn("text-xs tabular-nums", c.fill_rate < c.baseline_fill_rate * 0.85 ? "text-danger" : "text-muted")}>
                            {pct(c.fill_rate, 0)}
                          </span>
                        </div>
                      </td>
                      <td className="px-2 py-2.5">
                        <span className={cn("text-xs tabular-nums", c.error_rate > c.baseline_error_rate * 2 ? "text-danger" : "text-muted")}>
                          {pct(c.error_rate, 2)}
                        </span>
                        <span className="ml-1 text-2xs text-subtle">
                          ({signedPct(((c.error_rate - c.baseline_error_rate) / (c.baseline_error_rate || 1)) * 100, 0)})
                        </span>
                      </td>
                      <td className="px-2 py-2.5 text-right text-xs tabular-nums text-muted">
                        {compact(c.actual_impressions)}
                        <span className="text-subtle"> / {compact(c.expected_impressions)}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <span className={cn("text-sm font-semibold tabular-nums", c.revenue_at_risk > 5000 ? "text-danger" : c.revenue_at_risk > 0 ? "text-warning" : "text-subtle")}>
                          {c.revenue_at_risk > 0 ? money(c.revenue_at_risk) : "—"}
                        </span>
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
