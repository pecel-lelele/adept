"use client";

import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/api/types";

// Official UN SDG icon colours, goals 1–17
const SDG_COLOURS: Record<number, string> = {
  1: "#E5243B", 2: "#DDA63A", 3: "#4C9F38", 4: "#C5192D", 5: "#FF3A21",
  6: "#26BDE2", 7: "#FCC30B", 8: "#A21942", 9: "#FD6925", 10: "#DD1367",
  11: "#FD9D24", 12: "#BF8B2E", 13: "#3F7E44", 14: "#0A97D9", 15: "#56C02B",
  16: "#00689D", 17: "#19486A",
};

type SdgLink = components["schemas"]["SdgLink"];

function viaLabel(via: string, labels: Map<string, string>, t: ReturnType<typeof useTranslations>): string {
  const [kind, id] = via.split(":");
  const known = kind === "role" || kind === "skill" || kind === "pathway";
  return known ? `${t(`via.${kind}`)}${id ? `: ${labels.get(via) ?? id}` : ""}` : via;
}

export function SdgLinkCards({
  links,
  labels,
}: {
  links: SdgLink[];
  labels: Map<string, string>;
}) {
  const t = useTranslations("sdg");

  return (
    <div className="a-sdg-cardgrid">
      {links.map((link, i) => {
        const goal = link.target.goal;
        const color = SDG_COLOURS[goal] ?? "#555";
        const isDirect = link.strength === "direct";
        const via = viaLabel(link.via ?? "", labels, t);

        return (
          <div key={`${link.target.target}-${link.via}-${i}`} className="a-sdg-flipwrap group">
            <div className="a-sdg-flipinner">
              {/* ── FRONT ── */}
              <div className="a-sdg-face a-sdg-front">
                {/* SDG colour square */}
                <div className="a-sdg-face-badge" style={{ backgroundColor: color }}>
                  <span className="a-sdg-face-label">SDG {link.target.target}</span>
                </div>
                {/* Short reason/hypothesis */}
                <p className="a-sdg-face-reason">{link.reason}</p>
                {/* Pills at bottom */}
                <div className="a-sdg-face-pills">
                  <span className="a-sdg-pill a-sdg-pill-via">{via}</span>
                  <Badge variant={isDirect ? "success" : "secondary"}>
                    {isDirect ? t("direct") : t("enabling")}
                  </Badge>
                  {!link.reviewed && (
                    <span className="a-sdg-pill a-sdg-pill-draft">{t("draft")}</span>
                  )}
                </div>
              </div>

              {/* ── BACK ── */}
              <div className="a-sdg-face a-sdg-back">
                <div className="a-sdg-back-header" style={{ borderLeftColor: color }}>
                  <span className="a-sdg-back-tag" style={{ backgroundColor: color }}>
                    SDG {link.target.target}
                  </span>
                  <span className="a-sdg-back-strength">
                    {isDirect ? t("direct") : t("enabling")}
                  </span>
                </div>
                {link.evidence ? (
                  <>
                    <div className="a-sdg-back-scroll">
                      <p className="a-sdg-back-evlabel">{t("evidence")}</p>
                      <p className="a-sdg-back-evtext">{link.evidence.note}</p>
                    </div>
                    <a
                      href={link.evidence.source.url}
                      className="a-sdg-back-src"
                      target="_blank"
                      rel="noreferrer"
                    >
                      ↗ {link.evidence.source.name}
                    </a>
                  </>
                ) : (
                  <p className="a-sdg-back-noev">{t("draft")}</p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

