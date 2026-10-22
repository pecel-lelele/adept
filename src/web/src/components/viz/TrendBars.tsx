export type TrendBar = {
  id: string;
  label: string;
  value: number;
  direction: "rising" | "stable" | "declining" | string;
};

/** Diverging bars: rising skills grow right (green), declining grow left (red). */
export function TrendBars({ items, max }: { items: TrendBar[]; max?: number }) {
  const top = max ?? Math.max(0.01, ...items.map((i) => Math.abs(i.value)));
  return (
    <div className="a-bars" role="list">
      {items.map((i) => {
        const width = Math.min(50, (Math.abs(i.value) / top) * 50);
        return (
          <div className="a-bar" role="listitem" key={i.id}>
            <span className="a-bar-label" title={i.label}>
              {i.label}
            </span>
            <span className="a-bar-track" aria-hidden="true">
              <span className="a-bar-fill" data-dir={i.direction} style={{ width: `${width}%` }} />
            </span>
            <span className="a-bar-value" title={i.value.toFixed(2)}>
              {i.direction === "rising" ? "▲" : i.direction === "declining" ? "▼" : "•"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
