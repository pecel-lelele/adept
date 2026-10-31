"use client";

import { ArrowDownRight, ArrowUpRight, ChevronDown } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useId, useState } from "react";

import { MetaBar } from "@/components/MetaBar";
import type { RecommendationMeta, Schemas } from "@/lib/api";

const ROLE_STEP = 5;

type RoleSignal = Schemas["TrendSignal"];

/** Below half of a role's skill weight with trend data, no direction is claimed. */
function insufficient(role: RoleSignal): boolean {
  return Boolean(role.insufficient_evidence) || (typeof role.trend_coverage === "number" && role.trend_coverage < 0.5);
}

function RoleList({ roles, title, direction, meta, organisation, snapshotDate }: {
  roles: RoleSignal[]; title: string; direction: "rising" | "declining" | "insufficient";
  meta: RecommendationMeta; organisation: boolean; snapshotDate?: string;
}) {
  const t = useTranslations("trends");
  const [expanded, setExpanded] = useState(false);
  const listId = useId();
  const hasMore = roles.length > ROLE_STEP;
  const previewRole = roles[ROLE_STEP];
  const href = (role: RoleSignal) => `${organisation ? "/org/plan?role=" : "/app/matches/"}${encodeURIComponent(role.entity_id)}${organisation ? "&" : "?"}scenario=${meta.scenario}${snapshotDate && !organisation ? `&snapshot_date=${encodeURIComponent(snapshotDate)}` : ""}`;
  const row = (role: RoleSignal, preview = false) => {
    const percent = typeof role.trend_coverage === "number" ? Math.round(role.trend_coverage * 100) : null;
    const coverage = percent === null ? undefined : t("trendCoverage", { percent });
    return (
      <li key={role.entity_id} className="radar-role-row" title={coverage}>
        <div className="radar-role-line">
          {preview ? <span className="radar-role-name">{role.label}</span> : <Link className="radar-role-name" href={href(role)} title={coverage ? `${role.label} · ${coverage}` : role.label}>{role.label}</Link>}
          {percent !== null ? <span className="radar-role-percent" aria-label={coverage}>{percent}%</span> : null}
          {direction !== "insufficient" ? <span className="a-trend" data-dir={direction}>{t(`direction.${direction}`)}</span> : null}
        </div>
        {percent !== null ? <span className="radar-coverage-track" aria-hidden><i style={{ width: `${Math.max(0, Math.min(100, percent))}%` }} /></span> : null}
      </li>
    );
  };
  return (
    <div className="radar-role-group" data-direction={direction} data-expanded={expanded}>
      <h3>
        {direction === "rising" ? <ArrowUpRight size={18} aria-hidden /> : direction === "declining" ? <ArrowDownRight size={18} aria-hidden /> : null}
        {title}<span className="radar-count">{roles.length}</span>
      </h3>
      <div className="radar-role-body">
        {roles.length ? <ul className="radar-role-list">{roles.slice(0, ROLE_STEP).map((role) => row(role))}</ul> : <p className="a-muted a-small">{t("noDirectionalRoles")}</p>}
        {hasMore ? <div className="radar-role-reveal">
          {!expanded && previewRole ? <ul className="radar-role-list radar-role-preview" aria-hidden="true" inert>{row(previewRole, true)}</ul> : null}
          <div id={listId} className="radar-role-extra" aria-hidden={!expanded} inert={!expanded}>
            <div><ul className="radar-role-list">{roles.slice(ROLE_STEP).map((role) => row(role))}</ul></div>
          </div>
        </div> : null}
      </div>
      {direction === "insufficient" ? <p className="radar-evidence-note a-muted a-small">{t("insufficientEvidenceHelp")}</p> : null}
      {hasMore ? <div className="radar-role-footer">
        <button type="button" className="radar-role-toggle" aria-expanded={expanded} aria-controls={listId} onClick={() => setExpanded(!expanded)}>
          {expanded ? t("showLess") : t("viewAll", { count: roles.length })}<ChevronDown size={14} aria-hidden />
        </button>
      </div> : null}
    </div>
  );
}

export function RoleDirectionsCard({ signals, meta, organisation = false, snapshotDate }: {
  signals: RoleSignal[]; meta: RecommendationMeta; organisation?: boolean; snapshotDate?: string;
}) {
  const t = useTranslations("trends");
  const thin = signals.filter((role) => role.entity_type === "role" && insufficient(role));
  const edition = `${meta.snapshot_date}:${meta.scenario}`;
  return (
    <section className="a-card a-pad radar-role-directions" aria-labelledby="h-role-directions">
      <h2 id="h-role-directions">{t("roleDirections")}</h2>
      <div className="radar-role-meta">
        <MetaBar meta={meta} />
        <div className="radar-source-chips">
          {meta.sources.map((source) => source.url ? (
            <a key={`${source.name}:${source.url}`} href={source.url} target="_blank" rel="noreferrer" title={source.retrieved_at}>{source.name}</a>
          ) : <span key={source.name} title={source.retrieved_at}>{source.name}</span>)}
        </div>
      </div>
      <div className="radar-role-columns">
        {(["rising", "declining"] as const).map((direction) => (
          <RoleList key={`${edition}:${direction}`} direction={direction}
            title={t(direction === "rising" ? "risingRoles" : "decliningRoles")}
            roles={signals.filter((role) => role.entity_type === "role" && role.direction === direction && !insufficient(role))
              .sort((a, b) => direction === "rising" ? b.growth_rate - a.growth_rate : a.growth_rate - b.growth_rate)}
            meta={meta} organisation={organisation} snapshotDate={snapshotDate} />
        ))}
        <RoleList key={`${edition}:insufficient`} roles={thin} direction="insufficient" title={t("insufficientEvidenceRoles")}
            meta={meta} organisation={organisation} snapshotDate={snapshotDate} />
      </div>
    </section>
  );
}
