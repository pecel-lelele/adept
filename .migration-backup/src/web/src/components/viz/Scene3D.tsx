import type { CSSProperties } from "react";

type Variant = "orbit" | "cards" | "grid" | "globe";

const v = (vars: Record<string, string | number>) => vars as CSSProperties;

function Block({ style }: { style: CSSProperties }) {
  return (
    <span className="a-block" style={style}>
      <i className="t" />
      <i className="f" />
      <i className="s" />
    </span>
  );
}

const SDG_COLOURS = ["#c5192d", "#4c9f38", "#ff3a21", "#26bde2", "#fcc30b", "#a21942"];
const CARD_COLOURS = ["#2f8f5b", "#14201a", "#d48a26", "#6b6fd6", "#c4553f"];
const LATITUDES: [string, string][] = [
  ["130px", "38px"],
  ["150px", "0px"],
  ["130px", "-38px"],
];

/**
 * Looping CSS-3D scenes, one per section (no WebGL, no library, ~0 KB JS):

 * orbit = trend radar (signal gyroscope),
 * cards = role matches (deck on a carousel), grid = team heatmap (cubes rising and falling),
 * globe = SDG impact (spinning sphere of goal-coloured meridians).
 * Decorative: hidden from assistive tech and paused for prefers-reduced-motion.
 */
export function Scene3D({ variant, className = "" }: { variant: Variant; className?: string }) {
  return (
    <div className={`a-scene a-s-${variant} ${className}`} aria-hidden="true">
      <div className="a-world">
        {variant === "orbit" ? (
          <>
            <span className="a-ringo" style={v({ "--r": "190px", "--t": "9s", "--c": "#2f8f5b" })}>
              <b />
            </span>
            <span className="a-ringo" style={v({ "--r": "150px", "--t": "7s", "--c": "#c4553f" })}>
              <b />
            </span>
            <span className="a-ringo" style={v({ "--r": "112px", "--t": "5s", "--c": "#d48a26" })}>
              <b />
            </span>
            <span className="a-core" />
          </>
        ) : null}
        {variant === "cards" ? (
          <>
            {[0, 1, 2, 3, 4].map((i) => (
              <span
                key={i}
                className="a-card3d"
                style={v({ "--i": i, "--c": CARD_COLOURS[i % CARD_COLOURS.length] ?? "#14201a" })}
              >
                <i style={v({ "--w": "80%" })} />
                <i style={v({ "--w": "55%" })} />
              </span>
            ))}
          </>
        ) : null}
        {variant === "grid" ? (
          <>
            {Array.from({ length: 16 }, (_, n) => (
              <Block
                key={n}
                style={v({
                  "--x": n % 4,
                  "--y": Math.floor(n / 4),
                  "--h": 14 + ((n * 7) % 5) * 8,
                  "--top": n % 3 === 0 ? "#c4c6ff" : "#e3e4ff",
                  "--front": n % 3 === 0 ? "#8e91e6" : "#b9bbf2",
                  "--side": n % 3 === 0 ? "#6b6fd6" : "#9fa2ea",
                })}
              />
            ))}
          </>
        ) : null}
        {variant === "globe" ? (
          <>
            {SDG_COLOURS.map((c, i) => (
              <span key={c} className="a-meridian" style={v({ "--i": i, "--c": c })} />
            ))}
            {LATITUDES.map(([r, z]) => (
              <span key={z} className="a-latitude" style={v({ "--r": r, "--z": z })} />
            ))}
          </>
        ) : null}
      </div>
    </div>
  );
}
