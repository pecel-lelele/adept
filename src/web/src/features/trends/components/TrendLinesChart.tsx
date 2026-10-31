"use client";

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

export type TrendLine = {
  key: string;
  label: string;
  color: string;
  change: number | null;
  points: { day: string; share: number | null }[];
};

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

/** Observed 7-day rolling share per skill: hover for exact values; gaps stay gaps. */
export function TrendLinesChart({ lines, label }: { lines: TrendLine[]; label: string }) {
  const config: ChartConfig = Object.fromEntries(lines.map((l) => [l.key, { label: l.label, color: l.color }]));
  const days = lines[0]?.points.map((p) => p.day) ?? [];
  const data = days.map((day, i) => ({
    day,
    ...Object.fromEntries(lines.map((l) => [l.key, l.points[i]?.share ?? null])),
  }));
  const change = new Map(lines.map((l) => [l.key, l.change]));
  const marker = (key: string) => {
    const c = change.get(key);
    return c === null || c === undefined || c === 0 ? "" : c > 0 ? " ▲" : " ▼";
  };

  return (
    <ChartContainer config={config} role="img" aria-label={label}>
      <LineChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: 4 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis dataKey="day" tickLine={false} axisLine={false} minTickGap={28} tickMargin={8} />
        <YAxis tickFormatter={pct} tickLine={false} axisLine={false} width={52} />
        <ChartTooltip content={<ChartTooltipContent formatValue={pct} />} />
        <ChartLegend content={<ChartLegendContent marker={marker} />} />
        {lines.map((l) => (
          <Line
            key={l.key}
            dataKey={l.key}
            type="monotone"
            stroke={`var(--color-${l.key})`}
            strokeWidth={2.25}
            dot={false}
            activeDot={{ r: 4 }}
            connectNulls={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );
}
