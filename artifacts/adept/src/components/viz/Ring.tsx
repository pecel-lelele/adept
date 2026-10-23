import type { CSSProperties } from "react";

/** Radial progress / score ring. `value` is 0..1. */
export function Ring({
  value,
  size = 96,
  stroke = 9,
  label,
  caption,
  colour = "var(--a-ink)",
}: {
  value: number;
  size?: number;
  stroke?: number;
  label?: string;
  caption?: string;
  colour?: string;
}) {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <span
      className="a-ring"
      style={{ width: size, height: size, "--ring": `${size}px`, "--ring-c": `${c}` } as CSSProperties}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--a-line)" strokeWidth={stroke} />
        <circle
          className="is-value"
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={colour}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - clamped)}
        />
      </svg>
      <span className="a-ring-label">
        <strong>{label ?? `${Math.round(clamped * 100)}%`}</strong>
        {caption && size >= 72 ? <small>{caption}</small> : null}
      </span>
    </span>
  );
}

/** Colour for a 0..1 fit score: strong, fair, weak. */
export function scoreColour(score: number): string {
  if (score >= 0.6) return "var(--a-up)";
  if (score >= 0.35) return "var(--a-warn)";
  return "var(--a-down)";
}
