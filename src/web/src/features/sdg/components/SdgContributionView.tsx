import Link from "next/link";
import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetaBar,
  PageHeader,
  SdgBadge,
} from "@/components";
import type { ApiResult, ScenarioId, Schemas } from "@/lib/api";
import { cn } from "@/lib/utils";

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
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      {data.goals_summary.map((g) => (
        <div
          key={g.goal}
          className={cn(
            "rounded-md border p-2 text-xs",
            g.link_count === 0 && "opacity-40",
            g.is_focus && "border-primary",
          )}
        >
          <div className="font-semibold">
            SDG {g.goal}
            {g.is_focus ? <span className="ml-1 text-primary">· {t("focus")}</span> : null}
          </div>
          <div className="text-muted-foreground">{g.label}</div>
          {g.link_count > 0 ? (
            <div className="mt-1">
              {t("linkCount", { count: g.link_count })} ({g.direct_count ?? 0} {t("direct")},{" "}
              {g.enabling_count ?? 0} {t("enabling")})
              {showPeople ? <div>{t("contributors", { count: g.contributors ?? 0 })}</div> : null}
            </div>
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
    <ul className="space-y-2 text-sm">
      {links.map((link, i) => (
        <li key={`${link.target.target}-${link.via}-${i}`} className="flex items-start gap-2">
          <SdgBadge target={link.target} />
          <div>
            <p>{link.reason}</p>
            <p className="text-xs text-muted-foreground">
              {via(link.via ?? "")} ·{" "}
              <Badge variant={link.strength === "direct" ? "success" : "secondary"}>
                {link.strength === "direct" ? t("direct") : t("enabling")}
              </Badge>{" "}
              {link.reviewed ? null : <span>· {t("draft")}</span>}
            </p>
            {link.evidence ? (
              <p className="text-xs text-muted-foreground">
                {t("evidence")}:{" "}
                <a
                  href={link.evidence.source.url}
                  className="underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  {link.evidence.source.name}
                </a>
                . {link.evidence.note}
              </p>
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
  return (
    <div className="space-y-4">
      <PageHeader title={title} description={t("description")}>
        <MetaBar meta={data.meta} />
      </PageHeader>
      {data.role_ids && data.role_ids.length > 0 ? (
        <p className="text-sm">{t("forRoles", { roles: data.role_ids.join(", ") })}</p>
      ) : data.scope === "person" ? (
        <p className="text-sm">
          {t("noRoleYet")}{" "}
          <Link href="/app/pathway/compare" className="underline">
            {t("compareRoles")}
          </Link>
        </p>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle>{t("goals")}</CardTitle>
        </CardHeader>
        <CardContent>
          <GoalGrid data={data} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{t("links")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs text-muted-foreground">{t("strengthHint")}</p>
          <LinkList links={data.links} />
        </CardContent>
      </Card>
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
  const tab = (active: boolean) =>
    cn("rounded-md px-2.5 py-1 text-sm", active ? "bg-primary text-primary-foreground" : "border");
  return (
    <section className="space-y-4">
      <nav className="flex flex-wrap gap-2">
        <Link href={`/org/sdg?scenario=${scenario}`} className={tab(!region)}>
          {t("scope.organisation")}
        </Link>
        {regions.ok
          ? regions.data.regions.map((r) => (
              <Link
                key={r}
                href={`/org/sdg?scenario=${scenario}&region=${encodeURIComponent(r)}`}
                className={tab(region === r)}
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
