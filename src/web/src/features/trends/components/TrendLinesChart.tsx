"use client";

import { useLocale } from "next-intl";
import { CartesianGrid, Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

import { formatValue, type TrendMode } from "../range";

type Point = { day: string; value: number | null };

export type TrendLine = {
  key: string;
  label: string;
  color: string;
  change: number | null;
  points: Point[];
  projection: Point[];
};

export const projectedKey = (key: string) => `${key}p`;

const time = (day: string) => Date.parse(`${day}T00:00:00Z`);

/** One row per plotted day. Missing days stay gaps; the projection starts at the last observation. */
export function chartRows(lines: TrendLine[]) {
  const rows = new Map<string, Record<string, number | null>>();
  const row = (day: string) => {
    const found = rows.get(day);
    if (found) return found;
    const fresh: Record<string, number | null> = { t: time(day) };
    rows.set(day, fresh);
    return fresh;
  };
  for (const line of lines) {
    for (const point of line.points) row(point.day)[line.key] = point.value;
    const lastObserved = [...line.points].reverse().find((p) => p.value !== null);
    if (line.projection.length && lastObserved) row(lastObserved.day)[projectedKey(line.key)] = lastObserved.value;
    for (const point of line.projection) row(point.day)[projectedKey(line.key)] = point.value;
  }
  return [...rows.values()].sort((a, b) => (a.t ?? 0) - (b.t ?? 0));
}

type LegendEntry = { dataKey?: string | number; color?: string };
type TooltipEntry = { dataKey?: string | number; value?: number | string | null; color?: string; payload?: Record<string, number | null> };

/** Smooth lines with a crosshair; gaps stay gaps and the "if this pace continues" part is dashed. */
export function TrendLinesChart({
  lines,
  label,
  mode,
  projectedLabel,
  projectedFrom,
}: {
  lines: TrendLine[];
  label: string;
  mode: TrendMode;
  projectedLabel: string;
  projectedFrom?: string | null;
}) {
  const locale = useLocale();
  const config: ChartConfig = Object.fromEntries(
    lines.flatMap((l) => [
      [l.key, { label: l.label, color: l.color }],
      [projectedKey(l.key), { label: `${l.label} · ${projectedLabel}`, color: l.color }],
    ]),
  );
  const data = chartRows(lines);
  const change = new Map(lines.map((l) => [l.key, l.change]));
  const marker = (key: string) => {
    const c = change.get(key);
    return c === null || c === undefined || c === 0 ? "" : c > 0 ? " ▲" : " ▼";
  };
  const date = new Intl.DateTimeFormat(locale, { month: "short", day: "numeric", timeZone: "UTC" });
  const longDate = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "UTC" });
  const value = (v: number) => formatValue(v, mode);

  return (
    <ChartContainer config={config} role="img" aria-label={label}>
      <LineChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: 4 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="t"
          type="number"
          scale="time"
          domain={["dataMin", "dataMax"]}
          tickFormatter={(t: number) => date.format(t)}
          tickLine={false}
          axisLine={false}
          minTickGap={36}
          tickMargin={8}
        />
        <YAxis
          tickFormatter={value}
          domain={[(min: number) => (mode === "raw" ? 0 : Math.max(0, Math.floor(min * 0.95))), "auto"]}
          tickLine={false}
          axisLine={false}
          width={52}
        />
        <ChartTooltip
          cursor={{ stroke: "var(--a-muted)", strokeWidth: 1 }}
          content={(props) => (
            <ChartTooltipContent
              active={props.active}
              label={typeof props.label === "number" ? longDate.format(props.label) : props.label}
              // On the last observed day the projection repeats the observation; show it once.
              payload={(props.payload as TooltipEntry[] | undefined)?.filter(
                (item) => !String(item.dataKey).endsWith("p") || typeof item.payload?.[String(item.dataKey).slice(0, -1)] !== "number",
              )}
              formatValue={value}
            />
          )}
        />
        <ChartLegend
          content={(props) => (
            // One entry per line: the dashed part is named by the marker line and the card's note.
            <ChartLegendContent marker={marker} payload={(props.payload as LegendEntry[] | undefined)?.filter((item) => !String(item.dataKey).endsWith("p"))} />
          )}
        />
        {projectedFrom ? (
          <ReferenceLine
            x={time(projectedFrom)}
            stroke="var(--a-muted)"
            strokeDasharray="2 4"
            label={{ value: projectedLabel, position: "insideTopLeft", fill: "var(--a-muted)", fontSize: 11 }}
          />
        ) : null}
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
        {lines.filter((l) => l.projection.length).map((l) => (
          <Line
            key={projectedKey(l.key)}
            dataKey={projectedKey(l.key)}
            type="monotone"
            stroke={`var(--color-${l.key})`}
            strokeWidth={1.75}
            strokeDasharray="5 5"
            dot={false}
            activeDot={{ r: 3 }}
            legendType="none"
            connectNulls={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );
}
