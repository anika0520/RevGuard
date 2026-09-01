"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { chartColor, clock, compact, money } from "@/lib/format";
import type { SeriesPoint, TrendPoint } from "@/lib/types";

const AXIS = { fill: chartColor.subtle, fontSize: 11 };

const tooltipStyle = {
  contentStyle: {
    background: chartColor.surface,
    border: `1px solid ${chartColor.line}`,
    borderRadius: 6,
    fontSize: 12,
    boxShadow: "0 8px 24px -8px rgb(0 0 0 / 0.25)",
  },
  labelStyle: { color: chartColor.subtle, marginBottom: 4 },
  itemStyle: { color: chartColor.muted },
};

const legendStyle = { fontSize: 11, color: chartColor.subtle };

export function RiskTrendChart({ data }: { data: TrendPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
        <defs>
          <linearGradient id="gRisk" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={chartColor.danger} stopOpacity={0.28} />
            <stop offset="100%" stopColor={chartColor.danger} stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="gProt" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={chartColor.success} stopOpacity={0.28} />
            <stop offset="100%" stopColor={chartColor.success} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={chartColor.line} vertical={false} />
        <XAxis
          dataKey="date"
          tick={AXIS}
          axisLine={false}
          tickLine={false}
          tickFormatter={(d) => new Date(d).toLocaleDateString([], { weekday: "short" })}
        />
        <YAxis
          yAxisId="risk"
          tick={AXIS}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => money(v)}
        />
        <YAxis
          yAxisId="protected"
          orientation="right"
          tick={AXIS}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => money(v)}
        />
        <Tooltip {...tooltipStyle} formatter={(v: number) => money(v, true)} />
        <Legend wrapperStyle={legendStyle} />
        <Area
          yAxisId="risk"
          type="monotone"
          dataKey="at_risk"
          name="Identified at risk (left axis)"
          stroke={chartColor.danger}
          strokeWidth={2}
          fill="url(#gRisk)"
        />
        <Line
          yAxisId="protected"
          type="monotone"
          dataKey="protected"
          name="Revenue protected (right axis)"
          stroke={chartColor.success}
          strokeWidth={2}
          strokeDasharray="5 3"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function PacingChart({
  data,
  onsetAt,
  remediatedAt,
}: {
  data: SeriesPoint[];
  onsetAt?: string | null;
  remediatedAt?: string | null;
}) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -4, bottom: 0 }}>
        <defs>
          <linearGradient id="gActual" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={chartColor.accent} stopOpacity={0.22} />
            <stop offset="100%" stopColor={chartColor.accent} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={chartColor.line} vertical={false} />
        <XAxis dataKey="ts" tick={AXIS} axisLine={false} tickLine={false} tickFormatter={clock} minTickGap={40} />
        <YAxis tick={AXIS} axisLine={false} tickLine={false} tickFormatter={compact} />
        <Tooltip
          {...tooltipStyle}
          labelFormatter={(v) => new Date(v).toLocaleString()}
          formatter={(v: number) => v.toLocaleString()}
        />
        <Legend wrapperStyle={legendStyle} />
        {onsetAt ? (
          <ReferenceArea x1={onsetAt} x2={data.at(-1)?.ts} fill={chartColor.danger} fillOpacity={0.05} />
        ) : null}
        {onsetAt ? (
          <ReferenceLine
            x={onsetAt}
            stroke={chartColor.danger}
            strokeDasharray="4 4"
            label={{ value: "Divergence", fill: chartColor.danger, fontSize: 10, position: "insideTopLeft" }}
          />
        ) : null}
        {remediatedAt ? (
          <ReferenceLine
            x={remediatedAt}
            stroke={chartColor.success}
            strokeDasharray="4 4"
            label={{ value: "Fix applied", fill: chartColor.success, fontSize: 10, position: "insideTopRight" }}
          />
        ) : null}
        <Area
          type="monotone"
          dataKey="cumulative_expected"
          name="Expected (cumulative)"
          stroke={chartColor.subtle}
          strokeDasharray="5 4"
          strokeWidth={1.75}
          fill="none"
        />
        <Area
          type="monotone"
          dataKey="cumulative_impressions"
          name="Actual (cumulative)"
          stroke={chartColor.accent}
          strokeWidth={2}
          fill="url(#gActual)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** Baseline band makes the anomaly obvious without reading a number. */
export function SignalChart({
  data,
  dataKey,
  baseline,
  color,
  unit = "%",
  onsetAt,
  height = 120,
}: {
  data: SeriesPoint[];
  dataKey: keyof SeriesPoint;
  baseline: number;
  color: string;
  unit?: string;
  onsetAt?: string | null;
  height?: number;
}) {
  const tolerance = Math.max(baseline * 0.12, 0.35);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 6, right: 6, left: -18, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={chartColor.line} vertical={false} />
        <XAxis dataKey="ts" tick={AXIS} axisLine={false} tickLine={false} tickFormatter={clock} minTickGap={50} />
        <YAxis tick={AXIS} axisLine={false} tickLine={false} width={44} />
        <Tooltip
          {...tooltipStyle}
          labelFormatter={(v) => new Date(v).toLocaleString()}
          formatter={(v: number) => `${v.toFixed(2)}${unit}`}
        />
        <ReferenceArea y1={baseline - tolerance} y2={baseline + tolerance} fill={chartColor.subtle} fillOpacity={0.14} />
        <ReferenceLine y={baseline} stroke={chartColor.subtle} strokeDasharray="4 4" />
        {onsetAt ? <ReferenceLine x={onsetAt} stroke={chartColor.danger} strokeDasharray="4 4" /> : null}
        <Line type="monotone" dataKey={dataKey as string} stroke={color} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function RiskBurndown({ points }: { points: { ts: string; risk: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={170}>
      <AreaChart data={points} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
        <defs>
          <linearGradient id="gBurn" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={chartColor.caution} stopOpacity={0.3} />
            <stop offset="100%" stopColor={chartColor.success} stopOpacity={0.03} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={chartColor.line} vertical={false} />
        <XAxis dataKey="ts" tick={AXIS} axisLine={false} tickLine={false} tickFormatter={clock} minTickGap={40} />
        <YAxis tick={AXIS} axisLine={false} tickLine={false} tickFormatter={(v) => money(v)} />
        <Tooltip
          {...tooltipStyle}
          labelFormatter={(v) => new Date(v).toLocaleString()}
          formatter={(v: number) => money(v, true)}
        />
        <Area
          type="monotone"
          dataKey="risk"
          name="Revenue at risk"
          stroke={chartColor.caution}
          strokeWidth={2}
          fill="url(#gBurn)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
