import type { CSSProperties, ReactNode } from "react";

/**
 * An organisation as a monochrome isometric paper model: an office tower whose windows light
 * up floor by floor (people learning), an annex with a rooftop garden, a team working around a
 * table on the plaza and people walking between the buildings. Motion lives in adept.css
 * (.a-org) and stops for reduced-motion users.
 */

const U = 15;
const CX = 268;
const CY = 205;
const COS = 0.866;
type Pt = [number, number];
const iso = (x: number, y: number, z: number): Pt => [CX + (x - y) * COS * U, CY + (x + y) * 0.5 * U - z * U];
const pts = (list: Pt[]) => list.map(([a, b]) => `${a.toFixed(1)},${b.toFixed(1)}`).join(" ");
const delay = (s: number) => ({ animationDelay: `${s}s` }) as CSSProperties;

/** Flat content (px, y down) on the face that looks toward +y (front-left). */
const faceY = (x: number, y: number, z: number) => {
  const [ox, oy] = iso(x, y, z);
  return `matrix(${COS},0.5,0,1,${ox.toFixed(1)},${oy.toFixed(1)})`;
};
/** Flat content (px, y down) on the face that looks toward +x (front-right). */
const faceX = (x: number, y: number, z: number) => {
  const [ox, oy] = iso(x, y, z);
  return `matrix(${COS},-0.5,0,1,${ox.toFixed(1)},${oy.toFixed(1)})`;
};

function Box({
  x,
  y,
  z = 0,
  w,
  d,
  h,
  tone = "plain",
  children,
  className,
  style,
}: {
  x: number;
  y: number;
  z?: number;
  w: number;
  d: number;
  h: number;
  tone?: "plain" | "ground" | "accent";
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
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

/** A grid of windows on one face; each lights up in turn. */
function Windows({ cols, rows, w, h, gapX, gapY, seed }: { cols: number; rows: number; w: number; h: number; gapX: number; gapY: number; seed: number }) {
  const out: ReactNode[] = [];
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      const k = r * cols + c;
      out.push(
        <rect
          key={k}
          x={gapX + c * (w + gapX)}
          y={gapY + r * (h + gapY)}
          width={w}
          height={h}
          rx={1}
          className="a-org-win"
          style={delay(((k * 7 + seed * 3) % 23) * 0.32)}
        />,
      );
    }
  }
  return <>{out}</>;
}

function Person({ x, y, tone = "plain", className, style }: { x: number; y: number; tone?: "plain" | "accent"; className?: string; style?: CSSProperties }) {
  const [px, py] = iso(x, y, 0.3);
  return (
    <g className={className} style={style}>
      <rect x={px - 5} y={py - 19} width={10} height={19} rx={5} className={`a-org-body ${tone === "accent" ? "is-accent" : ""}`} />
      <circle cx={px} cy={py - 25} r={5} className={`a-org-head ${tone === "accent" ? "is-accent" : ""}`} />
    </g>
  );
}

export function OrgScene({ className = "" }: { className?: string }) {
  const walk = (() => {
    const a = iso(6.6, 9.2, 0.3);
    const b = iso(6.6, 12.2, 0.3);
    const c = iso(12.4, 12.2, 0.3);
    const e = iso(12.4, 8.6, 0.3);
    return `M${a[0]} ${a[1]} L${b[0]} ${b[1]} L${c[0]} ${c[1]} L${e[0]} ${e[1]}`;
  })();
  const [tx, ty] = iso(14.4, 10.9, 4.6);
  return (
    <svg className={`a-org ${className}`} viewBox="0 0 540 465" fill="none" aria-hidden>
      {/* ground and paths */}
      <Box x={0} y={0} w={18} d={15} h={0.3} tone="ground" />
      <polygon className="a-org-path" points={pts([iso(6, 8.8, 0.31), iso(7.2, 8.8, 0.31), iso(7.2, 12.8, 0.31), iso(6, 12.8, 0.31)])} />
      <polygon className="a-org-path" points={pts([iso(6, 11.6, 0.31), iso(13, 11.6, 0.31), iso(13, 12.8, 0.31), iso(6, 12.8, 0.31)])} />
      <polygon className="a-org-path" points={pts([iso(11.8, 8.2, 0.31), iso(13, 8.2, 0.31), iso(13, 12.8, 0.31), iso(11.8, 12.8, 0.31)])} />

      {/* tower */}
      <Box x={1.5} y={1.5} z={0.3} w={5} d={7} h={11}>
        <g transform={faceY(1.5, 8.5, 11.3)}>
          <Windows cols={5} rows={8} w={9} h={11} gapX={5} gapY={6.8} seed={1} />
        </g>
        <g transform={faceX(6.5, 8.5, 11.3)}>
          <Windows cols={7} rows={8} w={9} h={11} gapX={5.2} gapY={6.8} seed={2} />
        </g>
        <g transform={faceY(1.5, 8.5, 2.1)}>
          <rect x={27} y={0} width={21} height={27} rx={2} className="a-org-door" />
        </g>
      </Box>
      <Box x={2.6} y={3} z={11.3} w={2.6} d={3} h={0.9} />
      <g transform={`translate(${iso(3.9, 4.5, 12.2)[0]} ${iso(3.9, 4.5, 12.2)[1]})`}>
        <path d="M0 0v-30" className="a-org-mast" />
        <path d="M0 -30l16 5-16 5z" className="a-org-flag" />
      </g>

      {/* annex with rooftop garden */}
      <Box x={10} y={2} z={0.3} w={7} d={6} h={6}>
        <g transform={faceY(10, 8, 6.3)}>
          <Windows cols={6} rows={4} w={11} h={11} gapX={5.4} gapY={7} seed={3} />
        </g>
        <g transform={faceX(17, 8, 6.3)}>
          <Windows cols={5} rows={4} w={11} h={11} gapX={5.5} gapY={7} seed={4} />
        </g>
      </Box>
      <Box x={11} y={3} z={6.3} w={5} d={4} h={0.4} tone="accent" />
      {[
        [12.2, 4.2],
        [14.6, 5.6],
      ].map(([x, y]) => {
        const [bx, by] = iso(x ?? 0, y ?? 0, 6.7);
        return (
          <g key={`${x}-${y}`} className="a-org-tree">
            <path d={`M${bx} ${by}v-10`} className="a-org-mast" />
            <circle cx={bx} cy={by - 16} r={9} className="a-org-leaf" />
          </g>
        );
      })}

      {/* a team around a table, with an idea forming above them */}
      <Box x={13.2} y={10.1} z={0.3} w={2.4} d={1.6} h={1.1} />
      <Person x={13.3} y={9.6} />
      <Person x={15.9} y={10.4} tone="accent" />
      <Person x={13.5} y={12.4} />
      <Person x={15.8} y={12.3} />
      <g className="a-org-idea">
        <rect x={tx - 26} y={ty - 16} width={52} height={30} rx={6} className="a-org-board" />
        <path d={`M${tx - 18} ${ty + 6}l9-8 8 4 13-12`} className="a-org-trend" />
        <circle cx={tx + 12} cy={ty - 10} r={3} className="a-org-dot" />
      </g>

      {/* people walking between the buildings */}
      {[0, -4.5].map((d, i) => (
        <g key={d} className="a-org-walker" style={{ offsetPath: `path('${walk}')`, ...delay(d) }}>
          <rect x={-5} y={-19} width={10} height={19} rx={5} className={`a-org-body ${i ? "is-accent" : ""}`} />
          <circle cx={0} cy={-25} r={5} className={`a-org-head ${i ? "is-accent" : ""}`} />
        </g>
      ))}

      {/* trees on the ground */}
      {[
        [16.8, 9.4],
        [8.6, 13.6],
        [3.6, 12.6],
      ].map(([x, y]) => {
        const [bx, by] = iso(x ?? 0, y ?? 0, 0.3);
        return (
          <g key={`g-${x}-${y}`} className="a-org-tree">
            <path d={`M${bx} ${by}v-12`} className="a-org-mast" />
            <circle cx={bx} cy={by - 19} r={10} className="a-org-leaf" />
          </g>
        );
      })}
    </svg>
  );
}
