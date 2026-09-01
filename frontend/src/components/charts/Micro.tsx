"use client";

import { bandColor, chartColor } from "@/lib/format";
import type { HealthBand } from "@/lib/types";

export function HealthGauge({
  score,
  band,
  size = 88,
  stroke = 7,
}: {
  score: number;
  band: HealthBand;
  size?: number;
  stroke?: number;
}) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.max(0, Math.min(100, score)) / 100);
  const color = bandColor[band];
  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={chartColor.line} strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 700ms ease, stroke 400ms ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-semibold leading-none tabular-nums"
          style={{ color, fontSize: size / 3.4 }}
        >
          {Math.round(score)}
        </span>
        {size >= 80 ? (
          <span className="mt-1 text-2xs uppercase tracking-wider text-subtle">health</span>
        ) : null}
      </div>
    </div>
  );
}

export function ConfidenceRing({ value, size = 52 }: { value: number; size?: number }) {
  const stroke = 5;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={chartColor.line} strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={chartColor.accent}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - value)}
          style={{ transition: "stroke-dashoffset 700ms ease" }}
        />
      </svg>
      <span className="absolute text-xs font-semibold tabular-nums text-accent">
        {Math.round(value * 100)}%
      </span>
    </div>
  );
}

export function Sparkline({
  values,
  color = chartColor.accent,
  width = 84,
  height = 24,
}: {
  values: number[];
  color?: string;
  width?: number;
  height?: number;
}) {
  if (!values.length) return <div style={{ width, height }} />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = width / Math.max(1, values.length - 1);
  const points = values
    .map((v, i) => `${(i * step).toFixed(1)},${(height - ((v - min) / span) * height).toFixed(1)}`)
    .join(" ");
  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}

/** Delivery rate vs plan, with a marker at the 100% target. */
export function PacingBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(160, value));
  const color =
    value >= 90 && value <= 125
      ? chartColor.success
      : value >= 70
      ? chartColor.warning
      : chartColor.danger;
  return (
    <div className="flex items-center gap-2">
      <div className="relative h-1.5 w-20 overflow-hidden rounded-full bg-elevated">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${(clamped / 160) * 100}%`, background: color }}
        />
        <div className="absolute inset-y-0 left-[62.5%] w-px bg-subtle" />
      </div>
      <span className="w-12 text-right text-xs tabular-nums" style={{ color }}>
        {value.toFixed(0)}%
      </span>
    </div>
  );
}

const WATERFALL = [
  chartColor.caution,
  chartColor.accent,
  chartColor.violet,
  chartColor.success,
  chartColor.warning,
];

export function CauseWaterfall({
  causes,
}: {
  causes: { label: string; confidence: number; cause: string }[];
}) {
  return (
    <div className="space-y-2.5">
      {causes.map((c, i) => (
        <div key={c.cause} className="space-y-1">
          <div className="flex items-baseline justify-between text-xs">
            <span className={i === 0 ? "font-medium text-fg" : "text-muted"}>{c.label}</span>
            <span className="font-semibold tabular-nums" style={{ color: WATERFALL[i % WATERFALL.length] }}>
              {(c.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-elevated">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${c.confidence * 100}%`, background: WATERFALL[i % WATERFALL.length] }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
