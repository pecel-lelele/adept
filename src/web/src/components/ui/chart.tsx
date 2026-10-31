"use client";

import * as React from "react";
import * as RechartsPrimitive from "recharts";

/**
 * shadcn/ui chart primitives (lean): a config maps each series key to a label and colour,
 * exposed as `--color-<key>` CSS variables for Recharts, plus a themed tooltip and legend.
 */
export type ChartConfig = Record<string, { label: string; color: string }>;

const ChartContext = React.createContext<ChartConfig | null>(null);

function useChart(): ChartConfig {
  const config = React.useContext(ChartContext);
  if (!config) throw new Error("useChart must be used inside <ChartContainer />");
  return config;
}

export function ChartContainer({
  config,
  className,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  config: ChartConfig;
  children: React.ComponentProps<typeof RechartsPrimitive.ResponsiveContainer>["children"];
}) {
  const style = Object.fromEntries(
    Object.entries(config).map(([key, item]) => [`--color-${key}`, item.color]),
  ) as React.CSSProperties;
  return (
    <ChartContext.Provider value={config}>
      <div className={["a-chart", className].filter(Boolean).join(" ")} style={style} {...props}>
        <RechartsPrimitive.ResponsiveContainer>{children}</RechartsPrimitive.ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  );
}

export const ChartTooltip = RechartsPrimitive.Tooltip;
export const ChartLegend = RechartsPrimitive.Legend;

type TooltipItem = { dataKey?: string | number; value?: number | string | null; color?: string };

export function ChartTooltipContent({
  active,
  payload,
  label,
  formatValue = (v) => String(v),
}: {
  active?: boolean;
  payload?: TooltipItem[];
  label?: string | number;
  formatValue?: (value: number) => string;
}) {
  const config = useChart();
  if (!active || !payload?.length) return null;
  const rows = [...payload]
    .filter((item) => typeof item.value === "number")
    .sort((a, b) => (b.value as number) - (a.value as number));
  return (
    <div className="a-chart-tooltip">
      <div className="a-chart-tooltip-label">{label}</div>
      {rows.map((item) => {
        const key = String(item.dataKey);
        return (
          <div key={key} className="a-chart-tooltip-row">
            <span className="a-chart-swatch" style={{ background: config[key]?.color ?? item.color }} />
            <span>{config[key]?.label ?? key}</span>
            <b>{formatValue(item.value as number)}</b>
          </div>
        );
      })}
    </div>
  );
}

type LegendItem = { dataKey?: string | number; color?: string };

export function ChartLegendContent({
  payload,
  marker,
}: {
  payload?: LegendItem[];
  /** Optional per-series text after the label (for example ▲ / ▼). */
  marker?: (key: string) => string;
}) {
  const config = useChart();
  if (!payload?.length) return null;
  return (
    <ul className="a-chart-legend">
      {payload.map((item) => {
        const key = String(item.dataKey);
        return (
          <li key={key}>
            <span className="a-chart-swatch" style={{ background: config[key]?.color ?? item.color }} />
            {config[key]?.label ?? key}
            {marker ? <span className="a-chart-marker">{marker(key)}</span> : null}
          </li>
        );
      })}
    </ul>
  );
}
