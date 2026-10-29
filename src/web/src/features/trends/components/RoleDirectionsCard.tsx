import Link from "next/link";
import { useTranslations } from "next-intl";

import { MetaBar } from "@/components/MetaBar";
import type { RecommendationMeta, Schemas } from "@/lib/api";

export function RoleDirectionsCard({ options, meta, organisation = false, snapshotDate }: {
  options: Schemas["RoleOption"][]; meta: RecommendationMeta; organisation?: boolean; snapshotDate?: string;
}) {
  const t = useTranslations("trends");
  return (
    <section className="a-card a-pad">
      <h2>{t("roleDirections")}</h2>
      <MetaBar meta={meta} />
      <div className="a-split">
        {(["rising", "declining"] as const).map((direction) => {
          const roles = options.filter((role) => role.trend_direction === direction)
            .sort((a, b) => direction === "rising" ? (b.trend_signal ?? 0) - (a.trend_signal ?? 0) : (a.trend_signal ?? 0) - (b.trend_signal ?? 0));
          return (
            <div key={direction}>
              <h3>{t(direction === "rising" ? "risingRoles" : "decliningRoles")}</h3>
              {roles.length ? <ul className="a-notes">
                {roles.map((role) => (
                  <li key={role.role_id}>
                    <Link href={`${organisation ? "/org/plan?role=" : "/app/matches/"}${encodeURIComponent(role.role_id)}${organisation ? "&" : "?"}scenario=${meta.scenario}${snapshotDate && !organisation ? `&snapshot_date=${encodeURIComponent(snapshotDate)}` : ""}`}>
                      {role.role_label}
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
