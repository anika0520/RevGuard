"use client";

import { useEffect, useRef, useState } from "react";
import { mutate } from "swr";
import type { GuardianEvent } from "@/lib/types";

const REVALIDATE_ON: Record<string, string[]> = {
  "incident.created": ["/api/metrics/overview", "/api/metrics/priority-queue?limit=5"],
  "incident.updated": ["/api/metrics/overview", "/api/metrics/priority-queue?limit=5"],
  "impact.recorded": ["/api/metrics/overview", "/api/impact"],
  "action.executed": ["/api/metrics/overview"],
  "analysis.completed": ["/api/metrics/overview", "/api/metrics/priority-queue?limit=5"],
  "world.reset": ["/api/metrics/overview", "/api/metrics/priority-queue?limit=5", "/api/impact"],
};

export function useLiveEvents(limit = 60) {
  const [events, setEvents] = useState<GuardianEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const seen = useRef(0);

  useEffect(() => {
    const source = new EventSource("/api/stream");
    source.onopen = () => setConnected(true);
    source.addEventListener("hello", () => setConnected(true));
    source.addEventListener("ping", () => setConnected(true));
    source.addEventListener("guardian", (raw) => {
      setConnected(true);
      try {
        const event = JSON.parse((raw as MessageEvent).data) as GuardianEvent;
        seen.current += 1;
        if (event.kind !== "metric.tick") {
          setEvents((prev) => [event, ...prev].slice(0, limit));
        }
        (REVALIDATE_ON[event.kind] ?? []).forEach((key) => mutate(key));
        if (event.kind === "metric.tick" && seen.current % 6 === 0) {
          mutate("/api/simulation/state");
        }
      } catch {
        /* ignore malformed frames */
      }
    });
    // EventSource retries on its own; only report offline once it has actually given up.
    source.onerror = () => setConnected(source.readyState === EventSource.OPEN);
    return () => source.close();
  }, [limit]);

  return { events, connected };
}
