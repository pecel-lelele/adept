/** Official UN SDG colours, goals 1-17. */
export const SDG_COLOURS: Record<number, string> = {
  1: "#e5243b", 2: "#dda63a", 3: "#4c9f38", 4: "#c5192d", 5: "#ff3a21", 6: "#26bde2",
  7: "#fcc30b", 8: "#a21942", 9: "#fd6925", 10: "#dd1367", 11: "#fd9d24", 12: "#bf8b2e",
  13: "#3f7e44", 14: "#0a97d9", 15: "#56c02b", 16: "#00689d", 17: "#19486a",
};

export type SdgTile = { goal: number; title: string; count?: number };

/** Coloured goal tiles; the title is the accessible name and tooltip. */
export function SdgTiles({ goals, large = false }: { goals: SdgTile[]; large?: boolean }) {
  return (
    <ul className="a-sdgs">
      {goals.map((g) => (
        <li
          key={g.goal}
          className={`a-sdg${large ? " is-large" : ""}`}
          style={{ background: SDG_COLOURS[g.goal] ?? "#555" }}
          title={g.title}
          aria-label={`SDG ${g.goal}: ${g.title}${g.count ? ` (${g.count})` : ""}`}
        >
          <strong>{g.goal}</strong>
          <small>{g.count ? `×${g.count}` : "SDG"}</small>
        </li>
      ))}
    </ul>
  );
}
