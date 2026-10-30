import Link from "next/link";
import { useTranslations } from "next-intl";

import { MetaBar } from "@/components/MetaBar";
import type { RecommendationMeta, Schemas } from "@/lib/api";

export function RoleDirectionsCard({ signals, meta, organisation = false, snapshotDate }: {
  signals: Schemas["TrendSignal"][]; meta: RecommendationMeta; organisation?: boolean; snapshotDate?: string;
}) {
  const t = useTranslations("trends");
  return (
    <section className="a-card a-pad">
      <h2>{t("roleDirections")}</h2>
      <MetaBar meta={meta} />
      <div className="a-split">
        {(["rising", "declining"] as const).map((direction) => {
          const roles = signals.filter((role) => role.entity_type === "role" && role.direction === direction)
            .sort((a, b) => direction === "rising" ? b.growth_rate - a.growth_rate : a.growth_rate - b.growth_rate);
          return (
            <div key={direction}>
              <h3>{t(direction === "rising" ? "risingRoles" : "decliningRoles")}</h3>
              {roles.length ? <ul className="a-notes">
                {roles.map((role) => (
                  <li key={role.entity_id}>
                    <Link href={`${organisation ? "/org/plan?role=" : "/app/matches/"}${encodeURIComponent(role.entity_id)}${organisation ? "&" : "?"}scenario=${meta.scenario}${snapshotDate && !organisation ? `&snapshot_date=${encodeURIComponent(snapshotDate)}` : ""}`}>
                      {role.label}
                    </Link>{" "}<span className="a-trend" data-dir={direction}>{t(`direction.${direction}`)}</span>
                  </li>
                ))}
              </ul> : <p className="a-muted a-small">{t("noDirectionalRoles")}</p>}
            </div>
          );
        })}
      </div>
    </section>
  );
}
