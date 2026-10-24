import type { CSSProperties, ReactNode } from "react";

/**
 * Monochrome isometric line art for the app's features. Each object is a recognisable thing
 * (a CV page, a radar scope, a podium, two forecast charts, a stair path, a globe, a join card,
 * a heatmap, a stamped review) with one looping motion that shows what the feature does.
 * Everything shares one isometric projection: grey line work on white, one green accent.
 * Motion lives in adept.css (.a-iso) and stops for reduced-motion users.
 */

export type FeatureArtVariant =
  | "cv"
  | "radar"
  | "match"
  | "scenario"
  | "path"
  | "sdg"
  | "invite"
  | "heatmap"
  | "review"
  | "roster"
  | "matrix"
  | "target"
  | "gantt"
  | "coins";

const U = 10; // one grid unit in viewBox pixels
const CX = 120;
const CY = 52;
const COS = 0.866;

type Pt = [number, number];
const iso = (x: number, y: number, z: number): Pt => [CX + (x - y) * COS * U, CY + (x + y) * 0.5 * U - z * U];
const pts = (list: Pt[]) => list.map(([a, b]) => `${a.toFixed(1)},${b.toFixed(1)}`).join(" ");
const path = (list: Pt[]) => "M" + list.map(([a, b]) => `${a.toFixed(1)} ${b.toFixed(1)}`).join(" L");

/** Transform for drawing flat content (px units, y down) on a face that faces +y. */
const faceY = (x: number, y: number, zTop: number) => {
  const [ox, oy] = iso(x, y, zTop);
  return `matrix(${COS},0.5,0,1,${ox.toFixed(1)},${oy.toFixed(1)})`;
};
/** Transform for drawing flat content (local units) on the ground plane, centred at (x, y, z). */
const ground = (x: number, y: number, z: number) => {
  const [ox, oy] = iso(x, y, z);
  return `matrix(${COS * U},${0.5 * U},${-COS * U},${0.5 * U},${ox.toFixed(1)},${oy.toFixed(1)})`;
};

type Tone = "plain" | "accent" | "soft";
const FILL: Record<Tone, [string, string, string]> = {
  plain: ["#ffffff", "#f3f7f4", "#e6ede8"],
  soft: ["#f6f9f6", "#eef3ef", "#e2eae4"],
  accent: ["#d5f9df", "#a8edba", "#81d99b"],
};

/** An isometric box: top, left (+y) and right (+x) faces. */
function Box({
  x,
  y,
  z = 0,
  w,
  d,
  h,
  tone = "plain",
  className,
  style,
  children,
}: {
  x: number;
  y: number;
  z?: number;
  w: number;
  d: number;
  h: number;
  tone?: Tone;
  className?: string;
  style?: CSSProperties;
  children?: ReactNode;
}) {
  const [top, left, right] = FILL[tone];
  const t = z + h;
  return (
    <g className={className} style={style} data-tone={tone}>
      <polygon points={pts([iso(x, y + d, z), iso(x + w, y + d, z), iso(x + w, y + d, t), iso(x, y + d, t)])} fill={left} />
      <polygon points={pts([iso(x + w, y, z), iso(x + w, y + d, z), iso(x + w, y + d, t), iso(x + w, y, t)])} fill={right} />
      <polygon points={pts([iso(x, y, t), iso(x + w, y, t), iso(x + w, y + d, t), iso(x, y + d, t)])} fill={top} />
      {children}
    </g>
  );
}

const Plate = ({ size = 8 }: { size?: number }) => <Box x={0} y={0} w={size} d={size} h={0.4} tone="soft" />;
const delay = (s: number) => ({ animationDelay: `${s}s` }) as CSSProperties;

/** CV page standing on the desk: a scan beam reads it and skill tags appear beside it. */
function Cv() {
  const lines: [number, number][] = [[16, 30], [22, 24], [28, 30], [34, 18], [40, 26]];
  return (
    <>
      <Plate />
      <Box x={1.2} y={4.4} z={0.4} w={3.8} d={0.25} h={4.8}>
        <g transform={faceY(1.2, 4.65, 5.2)}>
          <path d="M31 0h7v7z" className="a-iso-fold" />
          <circle cx={7} cy={8} r={4} className="a-iso-avatar" />
          <path d="M14 6.5h14M14 10h9" className="a-iso-ink" strokeWidth={2.2} strokeLinecap="round" />
          {lines.map(([yy, len]) => (
            <path key={yy} d={`M4 ${yy}h${len}`} className="a-iso-ink" strokeWidth={2} strokeLinecap="round" />
          ))}
          <g className="a-iso-scanline">
            <path d="M1 2h36" className="a-iso-beam" />
            <rect x={1} y={-6} width={36} height={8} className="a-iso-scanglow" />
          </g>
        </g>
      </Box>
      {[0, 1, 2].map((i) => (
        <Box key={i} x={5.7} y={1.1 + i * 1.45} z={0.4} w={1.7} d={1} h={0.3} tone={i === 0 ? "accent" : "plain"} className="a-iso-chip" style={delay(0.4 + i * 0.45)}>
          <path d={path([iso(6, 1.6 + i * 1.45, 0.7), iso(7.1, 1.6 + i * 1.45, 0.7)])} className={i === 0 ? "a-iso-ink is-accent" : "a-iso-ink"} strokeWidth={2} strokeLinecap="round" />
        </Box>
      ))}
    </>
  );
}

/** A round radar scope: the sweep turns and skill blips light up as it passes. */
function RadarArt() {
  const blips: [number, number, boolean][] = [
    [35, 2.4, true],
    [130, 1.5, true],
    [215, 2.9, false],
    [300, 1.9, true],
  ];
  return (
    <>
      <Plate />
      <g transform="translate(0 4)">
        <g transform={ground(4, 4, 0.4)}>
          <circle r={3.75} className="a-iso-disc-edge" vectorEffect="non-scaling-stroke" />
        </g>
      </g>
      <g transform={ground(4, 4, 0.4)}>
        <circle r={3.75} className="a-iso-disc" vectorEffect="non-scaling-stroke" />
        {[1.25, 2.5].map((r) => (
          <circle key={r} r={r} className="a-iso-ring" vectorEffect="non-scaling-stroke" />
        ))}
        <path d="M-3.75 0H3.75M0 -3.75V3.75" className="a-iso-ring" vectorEffect="non-scaling-stroke" />
        <g className="a-iso-spin">
          <path d="M0 0L3.7 0A3.7 3.7 0 0 0 2.83 -2.38Z" className="a-iso-sweep" />
          <path d="M0 0H3.7" className="a-iso-beam" vectorEffect="non-scaling-stroke" />
        </g>
        {blips.map(([deg, r, up]) => {
          const a = (deg * Math.PI) / 180;
          return (
            <circle
              key={deg}
              cx={(Math.cos(a) * r).toFixed(2)}
              cy={(Math.sin(a) * r).toFixed(2)}
              r={0.32}
              className={up ? "a-iso-blip is-up" : "a-iso-blip"}
              style={delay((deg / 360) * 4)}
            />
          );
        })}
        <circle r={0.28} className="a-iso-hub" />
      </g>
    </>
  );
}

/** A 1-2-3 podium: the best-fit role stands on top with its score badge filling up. */
function Match() {
  const steps: [number, number, string, boolean][] = [
    [1.4, 2.2, "2", false],
    [3.0, 3.2, "1", true],
    [4.6, 1.4, "3", false],
  ];
  const [bx, by] = iso(3.8, 4.1, 5.5);
  return (
    <>
      <Plate />
      {steps.map(([x, h, label, win]) => (
        <g key={label} className={win ? "a-iso-bob" : undefined}>
          <Box x={x} y={3.2} z={0.4} w={1.6} d={1.8} h={h} tone={win ? "accent" : "plain"}>
            <g transform={faceY(x, 5, 0.4 + h)}>
              <text x={8} y={h * 5 + 4.5} textAnchor="middle" className={win ? "a-iso-num is-accent" : "a-iso-num"}>
                {label}
              </text>
            </g>
          </Box>
          {win ? (
            <g>
              <circle cx={bx} cy={by} r={10} className="a-iso-badge" />
              <circle cx={bx} cy={by} r={10} pathLength={100} className="a-iso-score" transform={`rotate(-90 ${bx} ${by})`} />
              <path d={`M${bx - 4} ${by}l3 3 5-6`} className="a-iso-check" />
            </g>
          ) : null}
        </g>
      ))}
    </>
  );
}

/** Two forecast charts side by side: a gentle (moderate) and a steep (fast) AI scenario. */
function Scenario() {
  const panels: [number, string, boolean][] = [
    [0.6, "M3 29L10 27L17 24.5L24 22.5L30 20", false],
    [4.2, "M3 30L10 26L17 18L24 11L30 4", true],
  ];
  return (
    <>
      <Plate />
      {panels.map(([x, d, fast]) => (
        <Box key={x} x={x} y={4.2} z={0.4} w={3.3} d={0.25} h={3.6}>
          <g transform={faceY(x, 4.45, 4)}>
            {[9, 18, 27].map((yy) => (
              <path key={yy} d={`M3 ${yy}h28`} className="a-iso-grid" />
            ))}
            <path d="M3 33h28M3 3v30" className="a-iso-axis" />
            <path d={d} pathLength={100} className={fast ? "a-iso-chart is-accent" : "a-iso-chart"} style={delay(fast ? 0.9 : 0)} />
            {fast ? <circle cx={30} cy={4} r={2.4} className="a-iso-endpoint" /> : null}
          </g>
        </Box>
      ))}
    </>
  );
}

/** Stair steps to a flag: a learner dot climbs course by course. */
function PathArt() {
  const steps = [0.6, 1.4, 2.2, 3];
  const tops: Pt[] = steps.map((h, i) => iso(0.8 + i * 1.8 + 0.7, 3.3 + 0.7, 0.4 + h + 0.45));
  const d = path(tops);
  const [fx, fy] = iso(0.8 + 3 * 1.8 + 0.7, 4, 3.4);
  return (
    <>
      <Plate />
      {steps.map((h, i) => (
        <Box key={h} x={0.8 + i * 1.8} y={3.3} z={0.4} w={1.4} d={1.4} h={h} tone={i === 3 ? "accent" : "plain"}>
          {i < 3 ? (
            <path d={path([iso(1.1 + i * 1.8, 4.1, 0.4 + h), iso(1.9 + i * 1.8, 4.1, 0.4 + h)])} className="a-iso-ink" strokeWidth={1.8} strokeLinecap="round" />
          ) : null}
        </Box>
      ))}
      <path d={d} className="a-iso-dash" />
      <g className="a-iso-wave">
        <path d={`M${fx} ${fy}v-22l13 5.5-13 5.5`} className="a-iso-flag" />
      </g>
      <circle r={5} className="a-iso-dot" style={{ offsetPath: `path('${d}')` }} />
    </>
  );
}

/** A wireframe globe turning on a stand, with a goal orbiting and a leaf growing. */
function Sdg() {
  const [gx, gy] = iso(4, 4, 4.1);
  const r = 24;
  const orbit = `M${gx - 40} ${gy} a40 11 0 1 0 80 0 a40 11 0 1 0 -80 0`;
  return (
    <>
      <Plate />
      <Box x={3.1} y={3.1} z={0.4} w={1.8} d={1.8} h={0.7} />
      <path d={path([iso(4, 4, 1.1), [gx, gy + r]])} className="a-iso-axis" />
      <g transform={`rotate(-14 ${gx} ${gy})`}>
        <path d={orbit} className="a-iso-orbit" />
      </g>
      <circle cx={gx} cy={gy} r={r} className="a-iso-globe" />
      {[-12, 0, 12].map((dy) => (
        <ellipse key={dy} cx={gx} cy={gy + dy} rx={Math.sqrt(r * r - dy * dy)} ry={4.5} className="a-iso-ring" />
      ))}
      {[0, -1.2, -2.4].map((dl, i) => (
        <ellipse key={dl} cx={gx} cy={gy} rx={r} ry={r} className={i === 0 ? "a-iso-meridian is-accent" : "a-iso-meridian"} style={delay(dl)} />
      ))}
      <g transform={`rotate(-14 ${gx} ${gy})`}>
        <circle r={4} className="a-iso-dot is-orbit" style={{ offsetPath: `path('${orbit}')` }} />
      </g>
      <g className="a-iso-sway" style={{ transformOrigin: `${gx + 14}px ${gy - 19}px` }}>
        <path d={`M${gx + 14} ${gy - 19}c1-6 2-9 1-13`} className="a-iso-stem" />
        <path d={`M${gx + 15} ${gy - 30}c5-6 13-5 15-1c-5 5-12 5-15 1z`} className="a-iso-leaf" />
      </g>
    </>
  );
}

/** A join card with its code, and people walking in to join. */
function Invite() {
  const people: [number, number][] = [
    [6.2, 1.2],
    [6.6, 2.9],
    [7, 4.6],
  ];
  return (
    <>
      <Plate />
      <Box x={0.9} y={4.6} z={0.4} w={4.2} d={0.25} h={3}>
        <g transform={faceY(0.9, 4.85, 3.4)}>
          <path d="M5 6h16" className="a-iso-ink" strokeWidth={2.2} strokeLinecap="round" />
          {[0, 1, 2, 3].map((i) => (
            <g key={i}>
              <rect x={5 + i * 8.5} y={12} width={7} height={11} rx={1.5} className={i === 0 ? "a-iso-codebox is-accent" : "a-iso-codebox"} />
              <circle cx={8.5 + i * 8.5} cy={17.5} r={1.4} className="a-iso-codedot" style={delay(i * 0.35)} />
            </g>
          ))}
        </g>
      </Box>
      {people.map(([x, y], i) => {
        const [px, py] = iso(x, y, 0.4);
        return (
          <g key={x} className="a-iso-walk" style={delay(i * 0.9)}>
            <rect x={px - 5} y={py - 19} width={10} height={19} rx={5} className={i === 0 ? "a-iso-body is-accent" : "a-iso-body"} />
            <circle cx={px} cy={py - 25} r={5} className={i === 0 ? "a-iso-head is-accent" : "a-iso-head"} />
          </g>
        );
      })}
    </>
  );
}

/** Members x roles as a block heatmap: the gaps breathe; the two largest are highlighted. */
function Heatmap() {
  const hs = [1.6, 0.8, 2.4, 1.2, 0.6, 2, 1.4, 0.9, 1.8, 2.6, 0.7, 1.3];
  return (
    <>
      <Plate />
      {hs.map((h, k) => {
        const i = k % 4;
        const j = Math.floor(k / 4);
        return (
          <Box key={k} x={0.7 + i * 1.8} y={1.6 + j * 1.8} z={0.4} w={1.3} d={1.3} h={h} tone={k === 2 || k === 9 ? "accent" : "plain"} className="a-iso-pulse" style={delay((i + j) * 0.3)} />
        );
      })}
    </>
  );
}

/** A completion record gets its approval stamp. */
function Review() {
  const [cx, cy] = iso(4.4, 3.6, 2.1);
  return (
    <>
      <Plate />
      <Box x={1.6} y={1.4} z={0.4} w={3.8} d={5} h={0.25} />
      {[2.3, 3.1, 3.9].map((yy) => (
        <path key={yy} d={path([iso(2.2, yy, 0.65), iso(4.6, yy, 0.65)])} className="a-iso-ink" strokeWidth={2.2} strokeLinecap="round" />
      ))}
      <g className="a-iso-stamp">
        <circle cx={cx} cy={cy} r={13} className="a-iso-badge" />
        <path d={`M${cx - 6} ${cy}l4 4 8-9`} className="a-iso-check" />
      </g>
      <Box x={6} y={4.6} z={0.4} w={1.2} d={1.2} h={0.9} tone="accent" className="a-iso-bob" />
    </>
  );
}

/** A clipboard roster: members tick off their profiles one by one (intake status). */
function Roster() {
  const rows = [12, 21, 30, 39];
  return (
    <>
      <Plate />
      <Box x={1.4} y={4.3} z={0.4} w={4.8} d={0.25} h={4.6}>
        <g transform={faceY(1.4, 4.55, 5)}>
          <rect x={16} y={-2} width={16} height={5} rx={1.5} className="a-iso-codebox" />
          {rows.map((yy, i) => (
            <g key={yy}>
              <circle cx={6} cy={yy} r={3} className="a-iso-avatar" />
              <path d={`M12 ${yy}h${[20, 16, 22, 14][i]}`} className="a-iso-ink" strokeWidth={2.2} strokeLinecap="round" />
              <circle cx={41} cy={yy} r={3.6} className="a-iso-tickbox" />
              <path d={`M39 ${yy}l1.6 1.6 3-3.4`} className="a-iso-tick" style={delay(0.5 + i * 0.6)} />
            </g>
          ))}
        </g>
      </Box>
      <Box x={6.6} y={2} z={0.4} w={0.9} d={0.9} h={1.2} tone="accent" className="a-iso-bob" />
    </>
  );
}

/** A heatmap board: people in rows, skills in columns, gap strength as shade. */
function Matrix() {
  const shades = [
    [0.2, 0.7, 0.4, 0.9, 0.3],
    [0.5, 0.2, 0.8, 0.4, 0.6],
    [0.9, 0.4, 0.3, 0.7, 0.2],
    [0.3, 0.6, 0.5, 0.2, 0.8],
  ];
  return (
    <>
      <Plate />
      <Box x={0.9} y={4.4} z={0.4} w={6.2} d={0.25} h={4.6}>
        <g transform={faceY(0.9, 4.65, 5)}>
          {[0, 1, 2, 3, 4].map((c) => (
            <path key={c} d={`M${16 + c * 9} 5h6`} className="a-iso-ink" strokeWidth={2} strokeLinecap="round" />
          ))}
          {shades.map((row, r) => (
            <g key={r}>
              <path d={`M3 ${14 + r * 9}h8`} className="a-iso-ink" strokeWidth={2} strokeLinecap="round" />
              {row.map((o, c) => (
                <rect
                  key={c}
                  x={14 + c * 9}
                  y={10 + r * 9}
                  width={8}
                  height={7.5}
                  rx={1.4}
                  className="a-iso-cell"
                  style={{ ...delay((r + c) * 0.25), ["--o" as string]: o } as CSSProperties}
                />
              ))}
            </g>
          ))}
        </g>
      </Box>
    </>
  );
}

/** A target board on a stand: the recommended role is the one with the largest team gap. */
function Target() {
  return (
    <>
      <Plate />
      <Box x={3.4} y={3.9} z={0.4} w={1.2} d={0.6} h={0.8} />
      <Box x={1.6} y={4.3} z={1.2} w={4.8} d={0.2} h={4.8}>
        <g transform={faceY(1.6, 4.5, 6)}>
          {[20, 14, 8].map((r, i) => (
            <circle key={r} cx={24} cy={24} r={r} className={i === 2 ? "a-iso-bull is-accent" : "a-iso-bull"} />
          ))}
          <circle cx={24} cy={24} r={2.5} className="a-iso-hub" />
          <g className="a-iso-arrow">
            <path d="M24 24l26-16" className="a-iso-shaft" />
            <path d="M46 6l8-2-3 7" className="a-iso-fletch" />
          </g>
        </g>
      </Box>
    </>
  );
}

/** A plan board with Gantt bars: courses scheduled week by week for the group. */
function Gantt() {
  const bars: [number, number, number][] = [
    [0, 4, 18],
    [1, 14, 20],
    [2, 26, 16],
    [3, 34, 18],
  ];
  return (
    <>
      <Plate />
      <Box x={0.9} y={4.4} z={0.4} w={6.2} d={0.25} h={4.4}>
        <g transform={faceY(0.9, 4.65, 4.8)}>
          {[12, 24, 36, 48].map((x) => (
            <path key={x} d={`M${x} 4v38`} className="a-iso-grid" />
          ))}
          <path d="M2 4h58" className="a-iso-axis" />
          {bars.map(([r, x, w]) => (
            <rect key={r} x={x} y={9 + r * 9} width={w} height={6} rx={3} className={r === 0 ? "a-iso-bar is-accent" : "a-iso-bar"} style={delay(r * 0.35)} />
          ))}
          <path d="M30 4v38" className="a-iso-today" />
        </g>
      </Box>
    </>
  );
}

/** Coin stacks: HRD Corp-claimable courses funded by the training levy; a new coin drops in. */
function Coins() {
  const stacks: [number, number, number][] = [
    [2.2, 4.6, 3],
    [4.2, 3.4, 5],
    [5.6, 5.2, 4],
  ];
  const coin = (cx: number, cy: number, key: string, cls = "") => (
    <g key={key} className={cls}>
      <path d={`M${cx - 13} ${cy}v4a13 6.5 0 0 0 26 0v-4`} className="a-iso-coin-side" />
      <ellipse cx={cx} cy={cy} rx={13} ry={6.5} className="a-iso-coin" />
    </g>
  );
  return (
    <>
      <Plate />
      {stacks.map(([x, y, n], k) => {
        const [cx, cy] = iso(x, y, 0.4);
        return (
          <g key={k}>
            {Array.from({ length: n }, (_, i) => coin(cx, cy - 4 - i * 4.5, `${k}-${i}`))}
            {k === 1 ? (
              <g className="a-iso-drop">
                {coin(cx, cy - 4 - n * 4.5, "drop", "is-accent")}
                <text x={cx} y={cy - 2 - n * 4.5} textAnchor="middle" className="a-iso-rm">
                  RM
                </text>
              </g>
            ) : null}
          </g>
        );
      })}
    </>
  );
}

const ART: Record<FeatureArtVariant, () => ReactNode> = {
  cv: Cv,
  radar: RadarArt,
  match: Match,
  scenario: Scenario,
  path: PathArt,
  sdg: Sdg,
  invite: Invite,
  heatmap: Heatmap,
  review: Review,
  roster: Roster,
  matrix: Matrix,
  target: Target,
  gantt: Gantt,
  coins: Coins,
};

export function FeatureArt({ variant, className }: { variant: FeatureArtVariant; className?: string }) {
  const Art = ART[variant];
  return (
    <svg className={`a-iso${className ? ` ${className}` : ""}`} viewBox="0 0 240 150" fill="none" aria-hidden data-variant={variant}>
      <g className="a-iso-lines">
        <Art />
      </g>
    </svg>
  );
}
