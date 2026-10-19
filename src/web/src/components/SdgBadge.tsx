import type { Schemas } from "@/lib/api";

// Official UN SDG icon colours, goals 1-17.
const SDG_COLOURS = [
  "#E5243B", "#DDA63A", "#4C9F38", "#C5192D", "#FF3A21", "#26BDE2", "#FCC30B", "#A21942",
  "#FD6925", "#DD1367", "#FD9D24", "#BF8B2E", "#3F7E44", "#0A97D9", "#56C02B", "#00689D",
  "#19486A",
];

export function SdgBadge({ target }: { target: Schemas["SdgTarget"] }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-semibold text-white"
      style={{ backgroundColor: SDG_COLOURS[target.goal - 1] ?? "#555" }}
      title={target.label}
    >
      SDG {target.target}
    </span>
  );
}
