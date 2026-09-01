"use client";

import { ChevronDown, Pause, Play, RefreshCw, RotateCcw, Zap } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import useSWR, { mutate } from "swr";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { api, fetcher } from "@/lib/api";
import type { SimState } from "@/lib/types";
import { cn } from "@/lib/utils";

const SPEEDS = [1, 10, 60, 300];
const SCENARIOS = [
  { id: "vast_spike", label: "VAST error spike" },
  { id: "targeting_change", label: "Targeting restriction" },
  { id: "supply_collapse", label: "Supply collapse" },
  { id: "auction_squeeze", label: "Auction squeeze" },
  { id: "data_outage", label: "Data feed outage" },
];

export function ControlBar() {
  const { data: sim } = useSWR<SimState>("/api/simulation/state", fetcher, { refreshInterval: 3000 });
  const [busy, setBusy] = useState(false);
  const [menu, setMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenu(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      mutate((key) => typeof key === "string" && key.startsWith("/api/"), undefined, { revalidate: true });
      toast.success(label);
    } catch {
      toast.error(`${label} failed — is the API running on :8000?`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="border-b border-line bg-elevated/60">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-2 px-6 py-2">
        <span className="mr-1 text-2xs font-medium uppercase tracking-wider text-subtle">
          Simulation
        </span>

        <Button
          size="sm"
          disabled={busy}
          onClick={() =>
            sim?.running
              ? run("Simulation paused", () => api.simPause())
              : run("Simulation running", () => api.simStart(10))
          }
        >
          {sim?.running ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          {sim?.running ? "Pause" : "Play"}
        </Button>

        <div className="inline-flex overflow-hidden rounded-md border border-line bg-surface">
          {SPEEDS.map((s) => (
            <button
              key={s}
              disabled={busy}
              onClick={() => run(`Speed set to ${s}×`, () => api.simStart(s))}
              className={cn(
                "px-2.5 py-1.5 text-xs tabular-nums transition-colors",
                sim?.speed === s ? "bg-accent text-white" : "text-muted hover:bg-elevated hover:text-fg"
              )}
            >
              {s}×
            </button>
          ))}
        </div>

        <Button size="sm" disabled={busy} onClick={() => run("World reset", () => api.simReset())}>
          <RotateCcw className="h-3.5 w-3.5" /> Reset
        </Button>

        <div className="relative" ref={menuRef}>
          <Button size="sm" disabled={busy} onClick={() => setMenu((v) => !v)}>
            Inject scenario <ChevronDown className="h-3.5 w-3.5" />
          </Button>
          {menu ? (
            <div className="absolute left-0 top-full z-50 mt-1 w-52 overflow-hidden rounded-md border border-line bg-surface shadow-pop">
              {SCENARIOS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => {
                    setMenu(false);
                    run(`Injected ${s.label.toLowerCase()}`, () => api.simInject(s.id));
                  }}
                  className="block w-full px-3 py-2 text-left text-xs text-muted transition-colors hover:bg-elevated hover:text-fg"
                >
                  {s.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <Button size="sm" variant="subtle" disabled={busy} onClick={() => run("Analysis complete", () => api.runAnalysis())}>
            <RefreshCw className="h-3.5 w-3.5" /> Run analysis
          </Button>
          <Button
            size="sm"
            variant="primary"
            disabled={busy}
            onClick={() => run("Replaying the Acme cascade", () => api.replayGolden())}
          >
            <Zap className="h-3.5 w-3.5" /> Replay reference incident
          </Button>
        </div>
      </div>
    </div>
  );
}
