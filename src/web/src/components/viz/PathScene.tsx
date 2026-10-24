import type { CSSProperties, ReactNode } from "react";

/**
 * "Where you are -> where you could be" as one isometric paper scene. Left: today's desk with a
 * paper stack while a robot arm takes the routine paperwork (work AI is automating). Middle: a
 * staircase of course books with a learner climbing it. Right: a raised platform where the
 * future role works at a laptop whose growth chart draws, beside a growing plant.
 * Monochrome on white, green only on the future side. Motion lives in adept.css (.a-path).
 */

const U = 15;
const CX = 250;
const CY = 110;
const COS = 0.866;
type Pt = [number, number];
const iso = (x: number, y: number, z: number): Pt => [CX + (x - y) * COS * U, CY + (x + y) * 0.5 * U - z * U];
const pts = (list: Pt[]) => list.map(([a, b]) => `${a.toFixed(1)},${b.toFixed(1)}`).join(" ");
const delay = (s: number) => ({ animationDelay: `${s}s` }) as CSSProperties;
const faceY = (x: number, y: number, z: number) => {
  const [ox, oy] = iso(x, y, z);
  return `matrix(${COS},0.5,0,1,${ox.toFixed(1)},${oy.toFixed(1)})`;
};

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
  tone?: "plain" | "soft" | "accent" | "dark";
  className?: string;
  style?: CSSProperties;
  children?: ReactNode;
}) {
  const t = z + h;
  return (
    <g className={className} style={style} data-tone={tone}>
      <polygon className="l" points={pts([iso(x, y + d, z), iso(x + w, y + d, z), iso(x + w, y + d, t), iso(x, y + d, t)])} />
      <polygon className="r" points={pts([iso(x + w, y, z), iso(x + w, y + d, z), iso(x + w, y + d, t), iso(x + w, y, t)])} />
      <polygon className="t" points={pts([iso(x, y, t), iso(x + w, y, t), iso(x + w, y + d, t), iso(x, y + d, t)])} />
      {children}
    </g>
  );
}

function Person({ at, accent = false, seated = false }: { at: Pt; accent?: boolean; seated?: boolean }) {
  const [px, py] = at;
  const h = seated ? 13 : 19;
  return (
    <g className={accent ? "a-path-person is-accent" : "a-path-person"}>
      <rect x={px - 5} y={py - h} width={10} height={h} rx={5} />
      <circle cx={px} cy={py - h - 6} r={5} />
    </g>
  );
}

export function PathScene({ className = "" }: { className?: string }) {
  const steps = [0.9, 1.8, 2.7, 3.6];
  const stepX = (i: number) => 5.3 + i * 1.28;
  // The learner walks from today's island, up the books, onto the future platform.
  const route: Pt[] = [
    iso(4.4, 3.8, 0.4),
    ...steps.map((h, i) => iso(stepX(i) + 0.64, 3.8, h)),
    iso(11.2, 3.8, 3.72),
  ];
  const walk = "M" + route.map(([a, b]) => `${a.toFixed(1)} ${b.toFixed(1)}`).join(" L");
  const [sx, sy] = iso(12, 1.6, 5.9);
  return (
    <svg className={`a-path ${className}`} viewBox="95 55 360 225" fill="none" aria-hidden>
      {/* today: a low island with a desk, a paper stack and a robot arm taking the papers */}
      <Box x={0} y={2.6} w={5} d={5} h={0.4} tone="soft" />
      <Box x={1.2} y={4.2} z={0.4} w={2.2} d={1.1} h={1} />
      {[0, 1, 2].map((i) => (
        <Box key={i} x={1.5} y={4.4} z={1.4 + i * 0.18} w={0.9} d={0.7} h={0.14} className="a-path-paper" style={delay(i * 0.9)} />
      ))}
      <Person at={iso(2.1, 6.1, 0.4)} seated />
      <g className="a-path-arm" style={{ transformOrigin: `${iso(3.9, 3.6, 0.4)[0]}px ${iso(3.9, 3.6, 0.4)[1]}px` }}>
        <path d={`M${iso(3.9, 3.6, 0.4)[0]} ${iso(3.9, 3.6, 0.4)[1]}v-22l-16 -8`} className="a-path-robot" />
        <circle cx={iso(3.9, 3.6, 0.4)[0]} cy={iso(3.9, 3.6, 0.4)[1] - 22} r={3} className="a-path-joint" />
        <path d={`M${iso(3.9, 3.6, 0.4)[0] - 16} ${iso(3.9, 3.6, 0.4)[1] - 30}l-5 3m5-3l-2 6`} className="a-path-robot" />
      </g>

      {/* the climb: a staircase of course books */}
      {steps.map((h, i) => (
        <Box key={h} x={stepX(i)} y={3} w={1.28} d={1.6} h={h} tone={i === steps.length - 1 ? "accent" : "plain"}>
          <g transform={faceY(stepX(i), 4.6, h)}>
            {Array.from({ length: Math.round(h / 0.45) }, (_, k) => (
              <path key={k} d={`M2 ${6 + k * 6.6}h${15.2}`} className="a-path-pages" />
            ))}
          </g>
        </Box>
      ))}
      <path d={walk} className="a-path-trail" />

      {/* where you could be: a raised platform, a laptop with a growth chart, a growing plant */}
      <Box x={10.4} y={0.6} w={4} d={4} h={3.6} />
      <Box x={10.6} y={0.8} z={3.6} w={3.6} d={3.6} h={0.12} tone="accent" />
      <Box x={11.1} y={1.3} z={3.72} w={1.9} d={0.9} h={0.8} />
      <Box x={11.3} y={1.45} z={4.52} w={1.4} d={0.08} h={1.1} />
      <g transform={faceY(11.3, 1.53, 5.62)}>
        <rect x={2} y={2} width={17} height={12} rx={1.5} className="a-path-screen" />
        <path d="M4 12l4-3 3 2 6-7" pathLength={100} className="a-path-chart" />
      </g>
      <Person at={iso(12.3, 2.9, 3.72)} accent />
      <Box x={13.4} y={1.1} z={3.72} w={0.6} d={0.6} h={0.5} />
      <g className="a-path-plant" style={{ transformOrigin: `${iso(13.7, 1.4, 4.22)[0]}px ${iso(13.7, 1.4, 4.22)[1]}px` }}>
        <path d={`M${iso(13.7, 1.4, 4.22)[0]} ${iso(13.7, 1.4, 4.22)[1]}v-16`} className="a-path-stem" />
        <path d={`M${iso(13.7, 1.4, 4.22)[0]} ${iso(13.7, 1.4, 4.22)[1] - 10}c-10-2-12-10-8-14c6 1 9 7 8 14z`} className="a-path-leaf" />
        <path d={`M${iso(13.7, 1.4, 4.22)[0]} ${iso(13.7, 1.4, 4.22)[1] - 15}c9-3 13-11 9-15c-7 2-10 8-9 15z`} className="a-path-leaf" />
      </g>
      <g className="a-path-spark">
        <circle cx={sx} cy={sy} r={10} className="a-path-badge" />
        <path d={`M${sx - 4} ${sy + 3}l4-6 4 6`} className="a-path-up" />
      </g>

      {/* the learner on the way */}
      <g className="a-path-walker" style={{ offsetPath: `path('${walk}')` }}>
        <rect x={-5} y={-19} width={10} height={19} rx={5} className="a-path-walker-body" />
        <circle cx={0} cy={-25} r={5} className="a-path-walker-body" />
      </g>
    </svg>
  );
}
