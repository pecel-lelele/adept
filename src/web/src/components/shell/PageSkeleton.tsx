/**
 * Shown by the route's loading.tsx while the server renders the next page: the same rhythm as
 * the real page (header, key numbers, two columns) so the switch is a fill-in, not a jump.
 */
export function PageSkeleton() {
  return (
    <div className="a-view a-skeleton" role="status" aria-live="polite" aria-busy="true">
      <span className="a-sr">Loading</span>
      <div className="a-skel-head">
        <i style={{ width: 120, height: 10 }} />
        <i style={{ width: "min(420px, 70%)", height: 30 }} />
        <i style={{ width: "min(560px, 90%)", height: 12 }} />
      </div>
      <div className="a-kpis a-skel-kpis" aria-hidden>
        {[0, 1, 2, 3].map((n) => (
          <div className="a-kpi" key={n}>
            <i style={{ width: "60%", height: 10 }} />
            <i style={{ width: "40%", height: 26 }} />
            <i style={{ width: "70%", height: 10 }} />
          </div>
        ))}
      </div>
      <div className="a-split" aria-hidden>
        <div className="a-card a-skel-card">
          {[90, 75, 82, 68, 88].map((w, n) => (
            <i key={n} style={{ width: `${w}%`, height: 14 }} />
          ))}
        </div>
        <div className="a-card a-skel-card">
          {[70, 85, 60].map((w, n) => (
            <i key={n} style={{ width: `${w}%`, height: 14 }} />
          ))}
        </div>
      </div>
    </div>
  );
}
