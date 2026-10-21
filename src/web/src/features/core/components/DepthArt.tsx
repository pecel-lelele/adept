import type { CSSProperties } from "react";
/** Lightweight isometric geometry inspired by the supplied reference. */
export function DepthArt({
  variant = "steps",
}: {
  variant?: "steps" | "people";
}) {
  return (
    <div className={`depth-art depth-${variant}`} aria-hidden="true">
      <div className="depth-board">
        {Array.from({ length: 9 }, (_, i) => (
          <span
            key={i}
            className="depth-block"
            style={{ "--i": i } as CSSProperties}
          />
        ))}
      </div>
    </div>
  );
}
