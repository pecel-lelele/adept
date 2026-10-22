export type StackPart = { key: string; label: string; value: number; colour: string };

/** One horizontal bar split into parts (e.g. invited / in progress / complete). */
export function StackBar({ parts }: { parts: StackPart[] }) {
  const total = parts.reduce((sum, p) => sum + p.value, 0);
  return (
    <div>
      <div className="a-stack-bar" role="img" aria-label={parts.map((p) => `${p.label}: ${p.value}`).join(", ")}>
        {total > 0
          ? parts.map((p) => (
              <span key={p.key} style={{ width: `${(p.value / total) * 100}%`, background: p.colour }} />
            ))
          : null}
      </div>
      <div className="a-keys">
        {parts.map((p) => (
          <span key={p.key}>
            <i style={{ background: p.colour }} />
            {p.label} <b>{p.value}</b>
          </span>
        ))}
      </div>
    </div>
  );
}
