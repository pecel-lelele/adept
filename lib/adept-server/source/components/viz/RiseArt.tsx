/**
 * Line-art isometric scene for Adept's core idea: one of your skills lifts off your stack and
 * travels to a future role, which then grows. Pure SVG (scales to any width, no 3D clipping on
 * phones); motion is CSS and stops for prefers-reduced-motion. Decorative only.
 */

type Pt = [number, number];

function pts(list: Pt[]): string {
  return list.map(([x, y]) => `${x},${y}`).join(" ");
}

/** An isometric slab: top diamond plus the two visible side faces. */
function Slab({
  cx,
  cy,
  a,
  b,
  d,
  top = "ln",
  side = "ln",
}: {
  cx: number;
  cy: number;
  a: number;
  b: number;
  d: number;
  top?: string;
  side?: string;
}) {
  return (
    <g>
      <polygon className={side} points={pts([[cx - a, cy], [cx, cy + b], [cx, cy + b + d], [cx - a, cy + d]])} />
      <polygon className={side} points={pts([[cx, cy + b], [cx + a, cy], [cx + a, cy + d], [cx, cy + b + d]])} />
      <polygon className={top} points={pts([[cx, cy - b], [cx + a, cy], [cx, cy + b], [cx - a, cy]])} />
    </g>
  );
}

/** Two short "text" strokes on a card top, drawn along the isometric axis. */
function CardLines({ cx, cy }: { cx: number; cy: number }) {
  return (
    <g stroke="#d3d8cd" strokeWidth={2} strokeLinecap="round">
      <line x1={cx - 30} y1={cy - 2} x2={cx + 4} y2={cy - 14} />
      <line x1={cx - 18} y1={cy + 6} x2={cx + 10} y2={cy - 4} />
    </g>
  );
}

export function RiseArt({ className = "" }: { className?: string }) {
  return (
    <svg className={`a-rise ${className}`} viewBox="0 0 420 300" role="presentation" aria-hidden="true">
      {/* ground */}
      <Slab cx={205} cy={232} a={178} b={60} d={10} top="ln-soft" side="ln-soft" />

      {/* your skill stack */}
      <Slab cx={125} cy={208} a={62} b={22} d={6} />
      <Slab cx={125} cy={196} a={62} b={22} d={6} />
      <Slab cx={125} cy={184} a={62} b={22} d={6} />
      <CardLines cx={125} cy={184} />

      {/* future-role pedestal */}
      <Slab cx={262} cy={96} a={56} b={20} d={86} />
      <g className="bob">
        <circle className="pulse" cx={262} cy={42} r={20} fill="var(--a-accent)" opacity={0.5} />
        <circle cx={262} cy={42} r={14} fill="#fff" stroke="#6f9a1f" strokeWidth={1.8} />
        <path d="M255 42l5 5 9-10" fill="none" stroke="#3f6212" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
      </g>

      {/* path from your skills to the role */}
      <path className="path" d="M150 158 C 168 92, 205 70, 238 84" />

      {/* the skill that moves */}
      <g className="lift">
        <Slab cx={125} cy={170} a={62} b={22} d={6} top="hl" side="hl" />
        <circle className="hl-fill" cx={105} cy={170} r={6} />
        <g stroke="#9fbf55" strokeWidth={2} strokeLinecap="round">
          <line x1={117} y1={168} x2={140} y2={160} />
        </g>
      </g>

      {/* demand growing */}
      <g>
        <rect className="bar ln" x={330} y={188} width={14} height={34} rx={3} />
        <rect className="bar ln" x={350} y={174} width={14} height={48} rx={3} />
        <rect className="bar hl" x={370} y={156} width={14} height={66} rx={3} />
      </g>
    </svg>
  );
}
