export type HeatRow = { id: string; label: string; cells: { id: string; value: number | null; suppressed?: boolean }[] };

function tone(value: number): { background: string; color: string } {
  const v = Math.max(0, Math.min(1, value));
  if (v === 0) return { background: "#eef1e7", color: "#33443a" };
  // light peach -> brick as the share of the team missing the skill grows
  const l = 92 - v * 42;
  // Relative luminance of this HSL(10, 60%, l) cell. Choose the stronger WCAG contrast.
  const chroma = (1 - Math.abs(2 * l / 100 - 1)) * 0.6;
  const minimum = l / 100 - chroma / 2;
  const linear = (channel: number): number =>
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  const luminance = 0.2126 * linear(minimum + chroma)
    + 0.7152 * linear(minimum + chroma / 6) + 0.0722 * linear(minimum);
  const color = (luminance + 0.05) / 0.05 >= 1.05 / (luminance + 0.05) ? "#000" : "#fff";
  return { background: `hsl(10 60% ${l}%)`, color };
}

/** Roles × skills grid; each cell is the share of the team below the required level. */
export function Heatmap({
  rows,
  columns,
  legend,
  suppressedLabel,
}: {
  rows: HeatRow[];
  columns: { id: string; label: string }[];
  legend: [string, string];
  suppressedLabel?: string;
}) {
  const template = `minmax(110px, 170px) repeat(${columns.length}, minmax(30px, 1fr))`;
  return (
    <div>
      <div className="a-heat" role="table">
        <div className="a-heat-row" role="row" style={{ gridTemplateColumns: template }}>
          <span />
          {columns.map((c) => (
            <span key={c.id} className="a-heat-head" role="columnheader" title={c.label}>
              {c.label}
            </span>
          ))}
        </div>
        {rows.map((r) => (
          <div key={r.id} className="a-heat-row" role="row" style={{ gridTemplateColumns: template }}>
            <span className="a-heat-label" role="rowheader" title={r.label}>
              {r.label}
            </span>
            {r.cells.map((c) => (
              <span key={c.id} className="a-heat-cell" role="cell" title={c.suppressed || c.value == null ? suppressedLabel : undefined} style={c.suppressed || c.value == null ? { background: "#ececec", color: "#444" } : tone(c.value)}>
                {c.suppressed || c.value == null ? <><span aria-hidden>—</span><span className="a-sr">{suppressedLabel}</span></> : c.value > 0 ? `${Math.round(c.value * 100)}` : ""}
              </span>
            ))}
          </div>
        ))}
      </div>
      <div className="a-legend">
        {legend[0]} <i /> {legend[1]}
      </div>
    </div>
  );
}
