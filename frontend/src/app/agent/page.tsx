"use client";

import { Terminal } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState, Skeleton } from "@/components/ui/Primitives";
import { fetcher } from "@/lib/api";
import type { Incident, ToolCall } from "@/lib/types";
import { cn } from "@/lib/utils";

type ToolDef = { name: string; description: string; inputSchema: Record<string, any> };

export default function AgentPage() {
  const { data: tools } = useSWR<ToolDef[]>("/api/tools", fetcher);
  const { data: incidents } = useSWR<Incident[]>("/api/incidents?active_only=true&limit=30", fetcher);
  const diagnosed = incidents?.filter((i) => i.diagnosis) ?? [];
  const [selected, setSelected] = useState<string | null>(null);
  const incidentId = selected ?? diagnosed[0]?.incident_id ?? null;

  const { data: bundle } = useSWR<{ incident: Incident; trace: ToolCall[] }>(
    incidentId ? `/api/incidents/${incidentId}` : null,
    fetcher
  );

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-fg">Agent Trace</h1>
        <p className="mt-1 text-sm text-muted">
          Every investigation is a sequence of typed tool calls. These definitions are already MCP-shaped JSON
          Schema — exposing them as an MCP server is a transport change, not a rewrite.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader className="flex-row items-center justify-between pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Terminal className="h-4 w-4 text-accent" /> Investigation trace
            </CardTitle>
            {diagnosed.length ? (
              <select
                value={incidentId ?? ""}
                onChange={(e) => setSelected(e.target.value)}
                className="rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs text-muted outline-none"
              >
                {diagnosed.map((i) => (
                  <option key={i.incident_id} value={i.incident_id}>
                    {i.incident_id} · {i.campaign_name}
                  </option>
                ))}
              </select>
            ) : null}
          </CardHeader>
          <CardContent className="pt-1">
            {!diagnosed.length ? (
              <EmptyState
                title="No investigations yet"
                hint="Open a war room and run an investigation — the tool calls appear here."
              />
            ) : !bundle ? (
              <Skeleton className="h-40 w-full" />
            ) : (
              <div className="space-y-1.5 font-mono text-xs">
                <p className="text-subtle">
                  USER: why is {bundle.incident.campaign_name} underdelivering?
                </p>
                {bundle.trace.map((t, i) => (
                  <details key={i} className="rounded-lg border border-line bg-elevated px-3 py-2">
                    <summary className="flex cursor-pointer items-center gap-2">
                      <span className="text-subtle">{i === bundle.trace.length - 1 ? "└─" : "├─"}</span>
                      <span className="text-accent">{t.name}</span>
                      <span className="text-subtle">({Object.keys(t.arguments).join(", ")})</span>
                      <span className="ml-auto tabular-nums text-subtle">{t.duration_ms}ms</span>
                      <span className={t.ok ? "text-success" : "text-danger"}>{t.ok ? "✓" : "✗"}</span>
                    </summary>
                    <div className="mt-2 space-y-1 border-t border-line pt-2 text-xs">
                      <p className="text-subtle">arguments</p>
                      <pre className="overflow-x-auto text-muted">{JSON.stringify(t.arguments, null, 2)}</pre>
                      <p className="text-subtle">result</p>
                      <p className="text-muted">{t.result_preview}</p>
                    </div>
                  </details>
                ))}
                {bundle.incident.diagnosis ? (
                  <p className="pt-2 text-muted">
                    <span className="text-success">ANSWER</span> · {bundle.incident.diagnosis.primary_cause.label} ·{" "}
                    {(bundle.incident.diagnosis.confidence * 100).toFixed(0)}% confidence ·{" "}
                    {bundle.incident.diagnosis.grounding_passed ? (
                      <span className="text-success">grounding passed</span>
                    ) : (
                      <span className="text-danger">grounding rejected</span>
                    )}
                  </p>
                ) : null}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Tool registry</CardTitle>
            <p className="text-xs text-subtle">{tools?.length ?? 0} tools · MCP-compatible JSON Schema</p>
          </CardHeader>
          <CardContent className="space-y-2 pt-1">
            {!tools ? (
              <Skeleton className="h-40 w-full" />
            ) : (
              tools.map((t) => (
                <details key={t.name} className="rounded-lg border border-line bg-elevated px-3 py-2">
                  <summary className="cursor-pointer text-xs">
                    <span className="font-mono text-accent">{t.name}</span>
                    <span className="ml-2 text-subtle">{t.description}</span>
                  </summary>
                  <pre className="mt-2 overflow-x-auto border-t border-line pt-2 font-mono text-2xs text-muted">
                    {JSON.stringify(t.inputSchema, null, 2)}
                  </pre>
                </details>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
