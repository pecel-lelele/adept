import type { Schemas } from "@/lib/api";
import { percent } from "@/lib/utils";

/** Explainable score: each component's weight x value, with its explanation. */
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
    <div className="space-y-2">
      <div className="text-2xl font-semibold">{percent(score)}</div>
      <ul className="space-y-2">
        {components.map((c) => (
          <li key={c.name} className="text-sm">
            <div className="flex justify-between">
              <span>{labels?.[c.name] ?? c.name}</span>
              <span className="tabular-nums text-muted-foreground">
                {percent(c.weight)} × {percent(c.value)} = {percent(c.weight * c.value)}
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded bg-muted">
              <div className="h-1.5 rounded bg-primary" style={{ width: percent(c.value) }} />
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">{c.explanation}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
