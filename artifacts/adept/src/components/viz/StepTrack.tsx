export type TrackStep = { id: string; label: string; state: "done" | "current" | "todo" };

/** A horizontal track of numbered dots: done (green), current (outlined), to do. */
export function StepTrack({ steps }: { steps: TrackStep[] }) {
  return (
    <ol className="a-track">
      {steps.map((s, i) => (
        <li className="a-track-step" data-state={s.state} key={s.id}>
          <span className="a-track-dot">{s.state === "done" ? "✓" : i + 1}</span>
          <small title={s.label}>{s.label}</small>
        </li>
      ))}
    </ol>
  );
}
