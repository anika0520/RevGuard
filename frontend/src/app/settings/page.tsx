"use client";

import { useEffect, useState } from "react";
import useSWR, { mutate } from "swr";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Primitives";
import { api, fetcher } from "@/lib/api";
import { cn } from "@/lib/utils";

type SettingsPayload = {
  demo_mode: boolean;
  dry_run: boolean;
  random_seed: number;
  llm_provider: string;
  llm_configured: boolean;
  health_weights: Record<string, number>;
  health_bands: Record<string, number>;
  anomaly: Record<string, number>;
  revenue_risk: Record<string, number>;
  current_window_hours: number;
  baseline_window_days: number;
  integrations: { name: string; status: string; detail: string }[];
};

const WEIGHT_LABELS: Record<string, string> = {
  pacing: "Pacing",
  fill_rate: "Fill rate",
  error_rate: "Error rate",
  supply_signal: "Supply signal",
  data_quality: "Data quality",
};

export default function SettingsPage() {
  const { data } = useSWR<SettingsPayload>("/api/settings", fetcher);
  const [weights, setWeights] = useState<Record<string, number> | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (data && !weights) setWeights(data.health_weights);
  }, [data, weights]);

  const total = weights ? Object.values(weights).reduce((a, b) => a + b, 0) : 0;

  const save = async () => {
    if (!weights) return;
    setSaving(true);
    try {
      await api.updateWeights(weights);
      mutate((k) => typeof k === "string" && k.startsWith("/api/"), undefined, { revalidate: true });
      toast.success("Business rules updated — the portfolio re-scored");
    } catch {
      toast.error("Could not update weights");
    } finally {
      setSaving(false);
    }
  };

  if (!data || !weights) return <Skeleton className="h-96 w-full" />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-fg">Settings</h1>
        <p className="mt-1 text-sm text-muted">
          Health weights are configurable business rules, not magic numbers. Change one and every campaign re-scores.
        </p>
      </div>

      <div className="rounded-xl border border-warning/25 bg-warning/[0.07] px-4 py-3 text-sm text-warning/90">
        Demo mode is on. All data sources are deterministic mock adapters (seed {data.random_seed}) and every
        outbound integration is in DRY_RUN — payloads are built and shown, never sent.
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Health score weights</CardTitle>
            <p className="text-xs text-subtle">
              Must total 100. Currently{" "}
              <span className={cn("tabular-nums", Math.abs(total - 100) < 0.01 ? "text-success" : "text-warning")}>
                {total.toFixed(0)}
              </span>
              .
            </p>
          </CardHeader>
          <CardContent className="space-y-4 pt-1">
            {Object.entries(weights).map(([key, value]) => (
              <div key={key}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-muted">{WEIGHT_LABELS[key] ?? key}</span>
                  <span className="tabular-nums text-muted">{value.toFixed(0)}</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={60}
                  value={value}
                  onChange={(e) => setWeights({ ...weights, [key]: Number(e.target.value) })}
                  className="w-full"
                />
              </div>
            ))}
            <div className="flex gap-2 pt-1">
              <button
                onClick={save}
                disabled={saving}
                className="rounded-lg bg-success/15 px-3.5 py-2 text-sm font-medium text-success transition-colors hover:bg-success/25 disabled:opacity-50"
              >
                {saving ? "Applying…" : "Apply & re-score portfolio"}
              </button>
              <button
                onClick={() => setWeights(data.health_weights)}
                className="rounded-lg border border-line px-3.5 py-2 text-sm text-muted hover:bg-elevated"
              >
                Reset
              </button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Connected systems</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 pt-1">
            {data.integrations.map((i) => (
              <div key={i.name} className="flex items-center gap-3 rounded-lg border border-line bg-elevated px-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-fg">{i.name}</p>
                  <p className="text-xs text-subtle">{i.detail}</p>
                </div>
                <span
                  className={cn(
                    "rounded-full border px-2 py-0.5 text-2xs font-semibold uppercase tracking-wider",
                    i.status.toLowerCase().includes("live")
                      ? "border-success/30 bg-success/10 text-success"
                      : "border-line bg-elevated text-muted"
                  )}
                >
                  {i.status}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Anomaly thresholds</CardTitle>
            <p className="text-xs text-subtle">
              An incident requires {data.anomaly.min_agreeing_signals} agreeing signals sustained across consecutive
              windows.
            </p>
          </CardHeader>
          <CardContent className="pt-1">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
              {Object.entries(data.anomaly).map(([k, v]) => (
                <div key={k} className="flex justify-between border-b border-line pb-1">
                  <dt className="text-subtle">{k.replace(/_/g, " ")}</dt>
                  <dd className="tabular-nums text-muted">{v}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Analysis windows & AI</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 pt-1 text-xs">
            <Row label="Current window" value={`${data.current_window_hours} hours`} />
            <Row label="Baseline window" value={`${data.baseline_window_days} days`} />
            <Row label="Risk range (conservative)" value={`x${data.revenue_risk.conservative_multiplier}`} />
            <Row label="Risk range (worst case)" value={`x${data.revenue_risk.worst_case_multiplier}`} />
            <Row
              label="LLM provider"
              value={data.llm_provider === "deterministic" ? "deterministic (no key required)" : data.llm_provider}
            />
            <div className="mt-3 rounded-lg border border-accent/20 bg-accent/[0.06] p-3 leading-relaxed text-accent/80">
              Set <code className="font-mono">LLM_PROVIDER=openai</code> or <code className="font-mono">gemini</code> plus an
              API key in <code className="font-mono">backend/.env</code> to swap in a real model. The evidence-grounding
              validator runs either way, and any output containing a number that is not in the evidence package is
              rejected and falls back to the deterministic engine.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-line pb-1.5">
      <span className="text-subtle">{label}</span>
      <span className="text-muted">{value}</span>
    </div>
  );
}
