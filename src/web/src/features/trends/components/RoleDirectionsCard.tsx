import Link from "next/link";
import { useTranslations } from "next-intl";

import { MetaBar } from "@/components/MetaBar";
import type { RecommendationMeta, Schemas } from "@/lib/api";

/** Role coverage fields (optional until the generated client includes them). */
type RoleSignal = Schemas["TrendSignal"] & { trend_coverage?: number | null; insufficient_evidence?: boolean };

/** Below half of a role's skill weight with trend data, no direction is claimed. */
function insufficient(role: RoleSignal): boolean {
  return Boolean(role.insufficient_evidence) || (typeof role.trend_coverage === "number" && role.trend_coverage < 0.5);
}

export function RoleDirectionsCard({ signals, meta, organisation = false, snapshotDate }: {
  signals: RoleSignal[]; meta: RecommendationMeta; organisation?: boolean; snapshotDate?: string;
}) {
  const t = useTranslations("trends");
  const href = (role: RoleSignal) => `${organisation ? "/org/plan?role=" : "/app/matches/"}${encodeURIComponent(role.entity_id)}${organisation ? "&" : "?"}scenario=${meta.scenario}${snapshotDate && !organisation ? `&snapshot_date=${encodeURIComponent(snapshotDate)}` : ""}`;
  const coverage = (role: RoleSignal) => typeof role.trend_coverage === "number"
    ? <span className="a-muted a-small"> · {t("trendCoverage", { percent: Math.round(role.trend_coverage * 100) })}</span>
    : null;
  const thin = signals.filter((role) => role.entity_type === "role" && insufficient(role));
  return (
    <section className="a-card a-pad">
      <h2>{t("roleDirections")}</h2>
      <MetaBar meta={meta} />
      <div className="a-split">
        {(["rising", "declining"] as const).map((direction) => {
          const roles = signals.filter((role) => role.entity_type === "role" && role.direction === direction && !insufficient(role))
            .sort((a, b) => direction === "rising" ? b.growth_rate - a.growth_rate : a.growth_rate - b.growth_rate);
          return (
            <div key={direction}>
              <h3>{t(direction === "rising" ? "risingRoles" : "decliningRoles")}</h3>
              {roles.length ? <ul className="a-notes">
                {roles.map((role) => (
                  <li key={role.entity_id}>
                    <Link href={href(role)}>
                      {role.label}
                    </Link>{" "}<span className="a-trend" data-dir={direction}>{t(`direction.${direction}`)}</span>{coverage(role)}
                  </li>
                ))}
              </ul> : <p className="a-muted a-small">{t("noDirectionalRoles")}</p>}
            </div>
          );
        })}
      </div>
      {thin.length ? (
        <div>
          <h3>{t("insufficientEvidenceRoles")}</h3>
          <p className="a-muted a-small">{t("insufficientEvidenceHelp")}</p>
          <ul className="a-notes">
            {thin.map((role) => (
              <li key={role.entity_id}>
                <Link href={href(role)}>{role.label}</Link>{" "}
                <span className="a-trend" data-dir="stable">{t("insufficientEvidence")}</span>{coverage(role)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
