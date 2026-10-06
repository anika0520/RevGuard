"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { fetcher } from "@/lib/api";
import type { Overview, SimState } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./ThemeToggle";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/campaigns", label: "Campaigns" },
  { href: "/incidents", label: "Incidents" },
  { href: "/impact", label: "Impact" },
  { href: "/agent", label: "Agent" },
  { href: "/settings", label: "Settings" },
];

export function TopNav({ onOpenPalette }: { onOpenPalette: () => void }) {
  const pathname = usePathname();
  const { data: overview } = useSWR<Overview>("/api/metrics/overview", fetcher, { refreshInterval: 8000 });
  const { data: sim } = useSWR<SimState>("/api/simulation/state", fetcher, { refreshInterval: 3000 });
  const { connected } = useLiveEvents(1);

  const simClock = sim ? new Date(sim.sim_clock) : null;

  return (
    <div className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-5 px-5">
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <img
            src="/revguard-logo.png"
            alt="RevGuard"
            className="h-9 w-9 shrink-0 rounded-md object-cover"
          />
          <span className="whitespace-nowrap text-[15px] font-semibold leading-none tracking-tight text-fg">
            <span className="text-accent">RevGuard</span>
          </span>
        </Link>

        <span className="hidden h-5 w-px shrink-0 bg-line lg:block" />

        <nav className="hidden shrink-0 items-center gap-0.5 lg:flex">
          {NAV.map(({ href, label }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "relative whitespace-nowrap rounded-md px-2.5 py-2 text-sm transition-colors",
                  active ? "font-medium text-fg" : "text-muted hover:bg-elevated hover:text-fg"
                )}
              >
                {label}
                {href === "/incidents" && overview?.incidents_open ? (
                  <span className="ml-1.5 rounded bg-danger/10 px-1.5 py-0.5 text-2xs font-semibold text-danger">
                    {overview.incidents_open}
                  </span>
                ) : null}
                {active ? (
                  <span className="absolute inset-x-2.5 -bottom-[13px] h-0.5 rounded-full bg-accent" />
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex shrink-0 items-center gap-2">
          <button
            onClick={onOpenPalette}
            aria-label="Search"
            className="hidden items-center gap-2 rounded-md border border-line bg-elevated px-2.5 py-1.5 text-xs text-subtle transition-colors hover:border-accent/40 hover:text-fg xl:flex"
          >
            <Search className="h-3.5 w-3.5" />
            <span className="w-24 text-left">Search…</span>
            <kbd className="rounded border border-line bg-surface px-1 py-px text-2xs">⌘K</kbd>
          </button>
          <button
            onClick={onOpenPalette}
            aria-label="Search"
            className="rounded-md border border-line bg-elevated p-2 text-subtle hover:text-fg xl:hidden"
          >
            <Search className="h-3.5 w-3.5" />
          </button>

          <div className="hidden items-center gap-2 whitespace-nowrap rounded-md border border-line bg-elevated px-2.5 py-1.5 md:flex">
            <span
              className={cn("h-1.5 w-1.5 shrink-0 rounded-full", connected ? "animate-pulse bg-success" : "bg-subtle")}
              title={connected ? "Event stream connected" : "Event stream offline"}
            />
            <span className="text-xs tabular-nums text-muted">
              {simClock
                ? simClock.toLocaleString([], {
                    day: "2-digit",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                  })
                : "--:--"}
            </span>
          </div>

          <span className="hidden whitespace-nowrap rounded border border-warning/30 bg-warning/10 px-2 py-1 text-2xs font-medium uppercase tracking-wide text-warning 2xl:inline">
            Demo data
          </span>

          <ThemeToggle />
        </div>
      </div>

      <nav className="flex items-center gap-0.5 overflow-x-auto border-t border-line px-4 py-1.5 lg:hidden">
        {NAV.map(({ href, label }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "whitespace-nowrap rounded-md px-3 py-1.5 text-sm",
                active ? "bg-elevated font-medium text-fg" : "text-muted"
              )}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
