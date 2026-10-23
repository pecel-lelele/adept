import type { Schemas } from "@/lib/api";

const pct = (v: number) => `${Math.round(v * 100)}%`;

/**
 * Explainable score: every part as weight × value = points, with its explanation. The points
 * add up to the score shown above them, so the arithmetic is visible.
 */
export function ScoreBreakdown({
  score,
  components,
  labels,
}: {
  score: number;
  components: Schemas["ScoreComponent"][];
  labels?: Record<string, string>;
}) {
  return (
    <div className="a-breakdown">
      <ul>
        {components.map((c) => (
          <li key={c.name}>
            <div className="a-breakdown-row">
              <strong>{labels?.[c.name] ?? c.name.replaceAll("_", " ")}</strong>
              <span>
                {pct(c.weight)} × {pct(c.value)} = <b>{(c.weight * c.value * 100).toFixed(1)}</b>
              </span>
            </div>
            <span className="a-scorebar-track" aria-hidden>
              <span style={{ width: pct(c.value), background: "var(--a-deep)", opacity: c.provided === false ? 0.35 : 1 }} />
            </span>
            <p>{c.explanation}</p>
          </li>
        ))}
      </ul>
      <div className="a-breakdown-total">
        <span>=</span>
        <strong>{(score * 100).toFixed(1)}</strong>
      </div>
    </div>
  );
}
