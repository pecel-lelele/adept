import { scoreColour } from "./Ring";

/** A 0..1 score as a labelled horizontal bar: "64%" then the bar. */
export function ScoreBar({ value, label }: { value: number; label?: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0)) * 100);
  return (
    <span className="a-scorebar" role="img" aria-label={label ? `${label}: ${pct}%` : `${pct}%`}>
      <strong>{pct}%</strong>
      <span className="a-scorebar-track" aria-hidden>
        <span style={{ width: `${pct}%`, background: scoreColour(value) }} />
      </span>
    </span>
  );
}

/** Level 1-5 as five pips. */
export function LevelPips({ level, max = 5, label }: { level: number; max?: number; label: string }) {
  return (
    <span className="a-pips" role="img" aria-label={label}>
      {Array.from({ length: max }, (_, i) => (
        <i key={i} data-on={i < level || undefined} />
      ))}
    </span>
  );
}
