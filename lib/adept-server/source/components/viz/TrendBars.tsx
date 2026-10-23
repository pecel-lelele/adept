export type TrendBar = {
  id: string;
  label: string;
  value: number;
  direction: "rising" | "stable" | "declining" | string;
};

const signed = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(2)}`;

/**
 * Diverging bars around a centre line: rising skills grow right (green), declining grow left
 * (red). Each row ends with the signed signal so the chart reads without colour. Optional
 * axis labels name both sides.
 */
export function TrendBars({
  items,
  max,
  axis,
}: {
  items: TrendBar[];
  max?: number;
  axis?: { down: string; up: string };
}) {
  const top = max ?? Math.max(0.01, ...items.map((i) => Math.abs(i.value)));
  return (
    <div className="a-diverge">
      {axis ? (
        <div className="a-diverge-axis" aria-hidden>
          <span />
          <span>
            <i>← {axis.down}</i>
            <i>{axis.up} →</i>
          </span>
          <span />
        </div>
      ) : null}
      <div className="a-bars" role="list">
        {items.map((i) => {
          const width = Math.max(1.5, Math.min(50, (Math.abs(i.value) / top) * 50));
          return (
            <div className="a-bar" role="listitem" key={i.id} data-dir={i.direction}>
              <span className="a-bar-label" title={i.label}>
                {i.label}
              </span>
              <span className="a-bar-track" aria-hidden="true">
                <span
                  className="a-bar-fill"
                  data-dir={i.direction}
                  data-side={i.value < 0 ? "left" : "right"}
                  style={{ width: `${width}%` }}
                />
              </span>
              <span className="a-bar-value">{signed(i.value)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
