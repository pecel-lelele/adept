import { Globe2, Link2, ShieldCheck, Target } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { Badge, ErrorState, Kpis, MetaBar, PageHeader, SdgBadge } from "@/components";
import { journeyStepCount } from "@/config/navigation";
import type { ApiResult, ScenarioId, Schemas } from "@/lib/api";
import { SDG_COLOURS } from "@/components/viz";

import {
  fetchMyContribution,
  fetchOrgContribution,
  fetchRegionContribution,
  fetchRegions,
} from "../api";
import { entityLabels } from "./entityLabels";

type Contribution = Schemas["SdgContribution"];

async function GoalGrid({ data }: { data: Contribution }) {
  const t = await getTranslations("sdg");
  const showPeople = data.scope !== "person";
  const goals = [...data.goals_summary].sort((a, b) => (b.hours_share ?? 0) - (a.hours_share ?? 0) || a.goal - b.goal);
  return (
    <div className="a-goalgrid">
      {goals.map((g) => (
        <div
          key={g.goal}
          className="a-goal"
          data-empty={g.link_count === 0 || undefined}
          data-focus={g.is_focus || undefined}
          style={{ background: SDG_COLOURS[g.goal] ?? "#555" }}
        >
          <b>{g.goal}</b>
          <span>{g.label}</span>
          {g.planned_hours ? <small>{t("hoursShare", { share: Math.round((g.hours_share ?? 0) * 100), hours: g.planned_hours })}</small> : null}
          {g.link_count > 0 ? (
            <small>
              {t("linkCount", { count: g.link_count })} · {g.direct_count ?? 0} {t("direct")}
              {showPeople ? ` · ${t("contributors", { count: g.contributors ?? 0 })}` : ""}
            </small>
          ) : null}
        </div>
      ))}
    </div>
  );
}

async function LinkList({ links, labels }: { links: Schemas["SdgLink"][]; labels: Map<string, string> }) {
  const t = await getTranslations("sdg");
  const via = (v: string) => {
    const [kind, id] = v.split(":");
    const known = kind === "role" || kind === "skill" || kind === "pathway";
    // Show the catalogue label; an id without one stays the id (never an invented name).
    return known ? `${t(`via.${kind}`)}${id ? `: ${labels.get(v) ?? id}` : ""}` : v;
  };
  return (
    <ul className="a-links">
      {links.map((link, i) => (
        <li key={`${link.target.target}-${link.via}-${i}`}>
          <SdgBadge target={link.target} />
          <div style={{ display: "grid", gap: 4, minWidth: 0 }}>
            <p>{link.reason}</p>
            <small>
              {via(link.via ?? "")} ·{" "}
              <Badge variant={link.strength === "direct" ? "success" : "secondary"}>
                {link.strength === "direct" ? t("direct") : t("enabling")}
              </Badge>{" "}
              {link.reviewed ? null : <span>· {t("draft")}</span>}
            </small>
            {link.evidence ? (
              <small>
                {t("evidence")}:{" "}
                <a href={link.evidence.source.url} className="a-link" target="_blank" rel="noreferrer">
                  {link.evidence.source.name}
                </a>
                . {link.evidence.note}
              </small>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}

async function ContributionBody({
  title,
  result,
  scenario,
}: {
  title: string;
  result: ApiResult<Contribution>;
  scenario: ScenarioId;
}) {
  const t = await getTranslations("sdg");
  const tp = await getTranslations("ui.page");
  if (!result.ok) return <ErrorState failure={result} />;
  const data = result.data;
  if (data.aggregation_status === "suppressed") return <section className="a-card"><h2>{title}</h2><p>{(await getTranslations("sdg"))(data.minimum_people ? "tooFewMembers" : "tooFewMembersUnknown", { count: data.minimum_people ?? 0 })}</p></section>;
  const labels = await entityLabels(scenario, data.scope === "person");
  const roleName = (id: string) => labels.get(`role:${id}`) ?? id;
  const linked = data.goals_summary.filter((g) => g.link_count > 0).length;
  const direct = data.links.filter((l) => l.strength === "direct").length;
  const reviewed = data.links.filter((l) => l.reviewed).length;
  return (
    <div className="a-view">
      <PageHeader eyebrow={data.scope === "person" ? tp("stepOf", { step: 6, total: journeyStepCount() }) : t("goals")} title={title} description={t("description")}>
        <MetaBar meta={data.meta} />
      </PageHeader>
      {data.role_ids && data.role_ids.length > 0 ? (
        <p className="a-notice" data-tone="info">
          {t("forRoles", { roles: data.role_ids.map(roleName).join(", ") })}
        </p>
      ) : data.scope === "person" ? (
        <p className="a-notice" data-tone="info">
          {t("noRoleYet")}{" "}
          <Link href={`/app/pathway/compare?scenario=${scenario}`} className="a-link">
            {t("compareRoles")}
          </Link>
        </p>
      ) : null}
      <Kpis
        items={[
          { label: tp("kGoalsLinked"), value: linked, unit: "/ 17", icon: <Globe2 size={15} />, tone: linked ? "up" : undefined, note: tp("kGoalsLinkedNote") },
          { label: tp("kDirect"), value: direct, icon: <Target size={15} />, note: tp("kDirectNote") },
          { label: tp("kEnabling"), value: data.links.length - direct, icon: <Link2 size={15} />, note: tp("kEnablingNote") },
          { label: tp("kReviewed"), value: reviewed, unit: `/ ${data.links.length}`, icon: <ShieldCheck size={15} />, note: tp("kReviewedNote") },
        ]}
      />
      {data.target_contributions?.length ? (
        <section className="a-card a-pad">
          <h2>{t("weightedTitle")}</h2>
          <p className="a-small a-muted">{t("weightedHint")}</p>
          <ul className="a-notes">
            {data.target_contributions.map((item) => (
              <li key={item.target.target}>
                <SdgBadge target={item.target} /> {t("hoursShare", { share: Math.round(item.hours_share * 100), hours: item.planned_hours })}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <section className="a-card" aria-labelledby="h-goals">
        <div className="a-card-head">
          <h2 id="h-goals">{t("goals")}</h2>
          <span className="a-muted a-small">{tp("goalsHint")}</span>
        </div>
        <GoalGrid data={data} />
      </section>
      <section className="a-card" aria-labelledby="h-links">
        <div className="a-card-head">
          <h2 id="h-links">{t("links")}</h2>
        </div>
        <p className="a-card-sub">{t("strengthHint")}</p>
        <LinkList links={data.links} labels={labels} />
      </section>
    </div>
  );
}

/** Person view: how the chosen path contributes. */
export async function SdgContributionView({
  roleId,
  scenario,
}: {
  roleId?: string;
  scenario: ScenarioId;
}) {
  const t = await getTranslations("sdg");
  return (
    <section>
      <ContributionBody title={t("title")} result={await fetchMyContribution(roleId, scenario)} scenario={scenario} />
    </section>
  );
}

/** Organisation view with a region switch (company / cohort → state). */
export async function OrgSdgView({
  region,
  role,
  scenario,
}: {
  region?: string;
  /** The target role chosen on the team plan; the default target when absent. */
  role?: string;
  scenario: ScenarioId;
}) {
  const t = await getTranslations("sdg");
  const regions = await fetchRegions();
  const result = region
    ? await fetchRegionContribution(region, scenario, role)
    : await fetchOrgContribution(scenario, role);
  const keep = role ? `&role=${encodeURIComponent(role)}` : "";
  return (
    <section className="a-stack">
      <nav className="a-scopes" aria-label={t("scope.organisation")}>
        <Link href={`/org/sdg?scenario=${scenario}${keep}`} aria-current={!region ? "page" : undefined}>
          {t("scope.organisation")}
        </Link>
        {regions.ok
          ? regions.data.regions.map((r) => (
              <Link
                key={r}
                href={`/org/sdg?scenario=${scenario}${keep}&region=${encodeURIComponent(r)}`}
                aria-current={region === r ? "page" : undefined}
              >
                {t("scope.region")}: {r}
              </Link>
            ))
          : null}
      </nav>
      <ContributionBody
        title={region ? t("regionTitle", { region }) : t("orgTitle")}
        result={result}
        scenario={scenario}
      />
    </section>
  );
}
