import { useId } from "react";

export type AdiMood = "idle" | "wave" | "think" | "talk" | "happy";

/**
 * Adi, Adept's guide. "Adi-" is Malay for excellent (adiwira = hero, adiguru = master teacher).
 * A green helper with a radar-dish antenna (the Future Skills Radar) and a leaf on its chest
 * (the SDG link). Pure SVG + CSS: no images, crisp at any size, motion off for reduced motion.
 */
export function AdiMascot({
  size = 96,
  mood = "idle",
  className = "",
  title,
}: {
  size?: number;
  mood?: AdiMood;
  className?: string;
  /** Accessible name; omit when the mascot is decorative. */
  title?: string;
}) {
  const id = useId().replace(/:/g, "");
  const body = `adi-body-${id}`;
  const face = `adi-face-${id}`;
  return (
    <svg
      className={`adi ${className}`}
      data-mood={mood}
      width={size}
      height={(size * 132) / 120}
      viewBox="0 0 120 132"
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <defs>
        <linearGradient id={body} x1="0" y1="0" x2="0.35" y2="1">
          <stop offset="0" stopColor="#4ade80" />
          <stop offset="0.55" stopColor="#22c55e" />
          <stop offset="1" stopColor="#15803d" />
        </linearGradient>
        <linearGradient id={face} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="1" stopColor="#e8faee" />
        </linearGradient>
      </defs>

      <ellipse className="adi-shadow" cx="60" cy="126" rx="30" ry="4.5" fill="#0d2a17" opacity="0.14" />

      <g className="adi-float">
        {/* antenna: a small radar dish sending signal arcs */}
        <g className="adi-antenna">
          <path d="M60 30 L60 18" stroke="#166534" strokeWidth="3" strokeLinecap="round" />
          <path d="M50 14 Q60 24 70 14" fill="none" stroke="#166534" strokeWidth="3.2" strokeLinecap="round" />
          <circle cx="60" cy="15" r="3.4" fill="#bbf7d0" stroke="#166534" strokeWidth="1.6" />
          <path className="adi-ping adi-ping-1" d="M53 7 Q60 1 67 7" fill="none" stroke="#22c55e" strokeWidth="2.2" strokeLinecap="round" />
          <path className="adi-ping adi-ping-2" d="M48 3 Q60 -6 72 3" fill="none" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" />
        </g>

        {/* arms */}
        <path className="adi-arm adi-arm-left" d="M18 78 Q6 84 10 96" fill="none" stroke="#16a34a" strokeWidth="8" strokeLinecap="round" />
        <path className="adi-arm adi-arm-right" d="M102 78 Q114 72 112 60" fill="none" stroke="#16a34a" strokeWidth="8" strokeLinecap="round" />

        {/* body */}
        <rect x="14" y="28" width="92" height="88" rx="36" fill={`url(#${body})`} />
        <ellipse cx="44" cy="44" rx="18" ry="8" fill="#ffffff" opacity="0.25" />

        {/* face screen */}
        <rect x="26" y="44" width="68" height="44" rx="20" fill={`url(#${face})`} />
        <g className="adi-eyes">
          <ellipse className="adi-eye" cx="47" cy="64" rx="5" ry="6.5" fill="#123321" />
          <ellipse className="adi-eye" cx="73" cy="64" rx="5" ry="6.5" fill="#123321" />
          <circle cx="48.8" cy="61.6" r="1.7" fill="#ffffff" />
          <circle cx="74.8" cy="61.6" r="1.7" fill="#ffffff" />
        </g>
        <circle cx="38" cy="75" r="4" fill="#fb7185" opacity="0.28" />
        <circle cx="82" cy="75" r="4" fill="#fb7185" opacity="0.28" />
        <path className="adi-smile" d="M53 76 Q60 82 67 76" fill="none" stroke="#123321" strokeWidth="2.6" strokeLinecap="round" />
        <ellipse className="adi-mouth" cx="60" cy="78" rx="5" ry="3.6" fill="#123321" />

        {/* leaf badge: the SDG link */}
        <path d="M60 106 C52 104 50 96 56 92 C62 95 64 101 60 106 Z" fill="#dcfce7" />
        <path d="M60 106 C66 103 70 97 66 92" fill="none" stroke="#dcfce7" strokeWidth="1.6" strokeLinecap="round" />
      </g>
    </svg>
  );
}
