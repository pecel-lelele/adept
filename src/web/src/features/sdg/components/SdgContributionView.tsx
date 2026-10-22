import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ApiError, Badge, MetaBar, PageHeader, SdgBadge } from "@/components";
import type { ApiResult, ScenarioId, Schemas } from "@/lib/api";
import { SDG_COLOURS } from "@/components/viz";

import {
  fetchMyContribution,
  fetchOrgContribution,
  fetchRegionContribution,
  fetchRegions,
} from "../api";

type Contribution = Schemas["SdgContribution"];

async function GoalGrid({ data }: { data: Contribution }) {
  const t = await getTranslations("sdg");
  const showPeople = data.scope !== "person";
  const goals = [...data.goals_summary].sort((a, b) => b.link_count - a.link_count || a.goal - b.goal);
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

async function LinkList({ links }: { links: Schemas["SdgLink"][] }) {
  const t = await getTranslations("sdg");
  const via = (v: string) => {
    const [kind, id] = v.split(":");
    const known = kind === "role" || kind === "skill" || kind === "pathway";
    return known ? `${t(`via.${kind}`)}${id ? `: ${id}` : ""}` : v;
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

async function ContributionBody({ title, result }: { title: string; result: ApiResult<Contribution> }) {
  const t = await getTranslations("sdg");
  if (!result.ok) return <ApiError message={result.message} />;
  const data = result.data;
  const linked = data.goals_summary.filter((g) => g.link_count > 0).length;
  return (
    <div className="a-stack" style={{ gap: 24 }}>
      <PageHeader eyebrow={t("goals")} title={title} description={t("description")}>
        <MetaBar meta={data.meta} />
      </PageHeader>
      {data.role_ids && data.role_ids.length > 0 ? (
        <p className="a-notice" data-tone="info">
          {t("forRoles", { roles: data.role_ids.join(", ") })}
        </p>
      ) : data.scope === "person" ? (
        <p className="a-notice" data-tone="info">
          {t("noRoleYet")}{" "}
          <Link href="/app/pathway/compare" className="a-link">
            {t("compareRoles")}
          </Link>
        </p>
      ) : null}
      <section className="a-card">
        <div className="a-card-head">
          <h2>{t("goals")}</h2>
          <span className="a-chip" data-tone="up">
            {linked} / 17
          </span>
        </div>
        <GoalGrid data={data} />
      </section>
      <section className="a-card">
        <div className="a-card-head">
          <h2>{t("links")}</h2>
        </div>
        <p className="a-small a-muted" style={{ marginTop: -8 }}>
          {t("strengthHint")}
        </p>
        <LinkList links={data.links} />
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
      <ContributionBody title={t("title")} result={await fetchMyContribution(roleId, scenario)} />
    </section>
  );
}

/** Organisation view with a region switch (company / cohort → state). */
export async function OrgSdgView({ region, scenario }: { region?: string; scenario: ScenarioId }) {
  const t = await getTranslations("sdg");
  const regions = await fetchRegions();
  const result = region
    ? await fetchRegionContribution(region, scenario)
    : await fetchOrgContribution(scenario);
  return (
    <section className="a-stack" style={{ gap: 18 }}>
      <nav className="a-scopes" aria-label={t("scope.organisation")}>
        <Link href={`/org/sdg?scenario=${scenario}`} aria-current={!region ? "page" : undefined}>
          {t("scope.organisation")}
        </Link>
        {regions.ok
          ? regions.data.regions.map((r) => (
              <Link
                key={r}
                href={`/org/sdg?scenario=${scenario}&region=${encodeURIComponent(r)}`}
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
      />
    </section>
  );
}
