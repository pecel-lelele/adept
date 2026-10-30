import { useTranslations } from "next-intl";

import { SdgTiles } from "@/components/viz";
import type { Schemas } from "@/lib/api";

/**
 * SDG tiles for a role, with each link's reason as visible text in a disclosure underneath, so
 * the reasons are reachable by keyboard and touch (not only as a hover title).
 */
export function MatchSdgTargets({ targets }: { targets: Schemas["SdgTarget"][] }) {
  const t = useTranslations("sdg");
  const goals = [...new Set(targets.map((target) => target.goal))].map((goal) => {
    const links = targets.filter((target) => target.goal === goal);
    const reason = links.map((link) => link.reason).filter(Boolean).join(" ");
    return {
      goal, reason,
      title: links.map((link) => `${link.target} ${link.label}. ${link.reason ?? ""}${link.strength ? ` (${t(link.strength)})` : ""}`).join(" "),
    };
  });
  return (
    <>
      <SdgTiles goals={goals} />
      <details className="a-sdg-why">
        <summary className="a-small a-link">{t("whyLinked")}</summary>
        <ul className="a-small" style={{ margin: "0.5rem 0 0", paddingLeft: "1.1rem", display: "grid", gap: 6 }}>
          {targets.map((link) => (
            <li key={`${link.goal}-${link.target}`}>
              <strong>
                {link.target} {link.label}
              </strong>
              {link.reason ? <> · {link.reason}</> : null}
              {link.strength ? <span className="a-muted"> ({t(link.strength)})</span> : null}
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}
