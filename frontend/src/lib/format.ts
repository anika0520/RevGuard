import type { HealthBand, Severity } from "./types";

export const money = (value: number, precise = false) => {
  if (!Number.isFinite(value)) return "$0";
  if (precise) return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1000) return `$${(value / 1000).toFixed(abs >= 100_000 ? 0 : 1)}K`;
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
};

export const moneyFull = (value: number) =>
  `$${(value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

export const num = (value: number) => (value ?? 0).toLocaleString();

export const compact = (value: number) => {
  const abs = Math.abs(value ?? 0);
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return `${value ?? 0}`;
};

export const pct = (value: number, digits = 1) => `${(value ?? 0).toFixed(digits)}%`;

export const signedPct = (value: number, digits = 1) =>
  `${value >= 0 ? "+" : ""}${(value ?? 0).toFixed(digits)}%`;

export const duration = (seconds: number) => {
  const s = Math.max(0, Math.round(seconds ?? 0));
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  return `${m}m`;
};

export const clock = (iso: string) =>
  new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });

export const stamp = (iso: string) =>
  new Date(iso).toLocaleString([], {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

export const bandLabel: Record<HealthBand, string> = {
  HEALTHY: "Healthy",
  WARNING: "Warning",
  HIGH_RISK: "High risk",
  CRITICAL: "Critical",
};

/** Chart strokes read the active theme so both modes stay legible. */
export const bandColor: Record<HealthBand, string> = {
  HEALTHY: "rgb(var(--success))",
  WARNING: "rgb(var(--warning))",
  HIGH_RISK: "rgb(var(--caution))",
  CRITICAL: "rgb(var(--danger))",
};

export const chartColor = {
  accent: "rgb(var(--accent))",
  success: "rgb(var(--success))",
  warning: "rgb(var(--warning))",
  danger: "rgb(var(--danger))",
  caution: "rgb(var(--caution))",
  violet: "rgb(139 92 246)",
  line: "rgb(var(--line))",
  muted: "rgb(var(--muted))",
  subtle: "rgb(var(--subtle))",
  surface: "rgb(var(--surface))",
};

export const bandChip: Record<HealthBand, string> = {
  HEALTHY: "border-success/30 bg-success/10 text-success",
  WARNING: "border-warning/30 bg-warning/10 text-warning",
  HIGH_RISK: "border-caution/30 bg-caution/10 text-caution",
  CRITICAL: "border-danger/30 bg-danger/10 text-danger",
};

export const severityChip: Record<Severity, string> = {
  CRITICAL: "border-danger/30 bg-danger/10 text-danger",
  HIGH: "border-caution/30 bg-caution/10 text-caution",
  MEDIUM: "border-warning/30 bg-warning/10 text-warning",
  LOW: "border-accent/30 bg-accent/10 text-accent",
};

export const statusChip: Record<string, string> = {
  OPEN: "border-danger/30 bg-danger/10 text-danger",
  INVESTIGATING: "border-accent/30 bg-accent/10 text-accent",
  AWAITING_APPROVAL: "border-warning/30 bg-warning/10 text-warning",
  ACTIONED: "border-accent/30 bg-accent/10 text-accent",
  RESOLVED: "border-success/30 bg-success/10 text-success",
  FALSE_POSITIVE: "border-line bg-elevated text-subtle",
};

export const signalLabel: Record<string, string> = {
  pacing_down: "Pacing down",
  overdelivery: "Overdelivery",
  fill_rate_down: "Fill rate down",
  vast_errors_up: "VAST errors up",
  eligible_inventory_down: "Inventory down",
  auction_pressure_up: "Auction pressure up",
  frequency_saturation: "Frequency saturation",
  data_quality_failure: "Data quality failure",
};

export const sourceChip: Record<string, string> = {
  GAM: "border-accent/25 bg-accent/10 text-accent",
  SPRINGSERVE: "border-violet-500/25 bg-violet-500/10 text-violet-600 dark:text-violet-300",
  ATHENA: "border-teal-500/25 bg-teal-500/10 text-teal-700 dark:text-teal-300",
  DERIVED: "border-line bg-elevated text-muted",
};
