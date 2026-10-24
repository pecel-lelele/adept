export type HeatRow = { id: string; label: string; cells: { id: string; value: number }[] };

function tone(value: number): { background: string; color: string } {
  const v = Math.max(0, Math.min(1, value));
  if (v === 0) return { background: "#eef1e7", color: "#6b766e" };
  // light peach -> brick as the share of the team missing the skill grows
  const l = 92 - v * 42;
  return { background: `hsl(10 60% ${l}%)`, color: v > 0.55 ? "#fff" : "#5b2618" };
}

/** Roles × skills grid; each cell is the share of the team below the required level. */
export function Heatmap({
  rows,
  columns,
  legend,
}: {
  rows: HeatRow[];
  columns: { id: string; label: string }[];
  legend: [string, string];
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
              <span key={c.id} className="a-heat-cell" role="cell" style={tone(c.value)}>
                {c.value > 0 ? `${Math.round(c.value * 100)}` : ""}
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
