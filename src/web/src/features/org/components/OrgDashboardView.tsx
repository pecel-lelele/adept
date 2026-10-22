import { ArrowRight, ArrowUpRight, Grid3x3, Leaf, Route, Users } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { Heatmap, Ring, Scene3D, SdgTiles, StackBar, StepTrack } from "@/components/viz";
import { fetchOrgContribution } from "@/features/sdg/api";
import type { ScenarioId, Schemas } from "@/lib/api";

import { fetchGaps, fetchMembers, fetchMyOrg, fetchPlan } from "../api";
import { JoinCodeCard } from "./JoinCodeCard";

/** The most useful columns of a heatmap: skills with the largest gap anywhere, max `n`. */
export function topGapSkills(gaps: Schemas["GapHeatmapResponse"], n: number) {
  const worst = new Map<string, number>();
  for (const c of gaps.cells) worst.set(c.skill_id, Math.max(worst.get(c.skill_id) ?? 0, c.gap));
  return gaps.skills
    .filter((s) => (worst.get(s.id) ?? 0) > 0)
    .sort((a, b) => (worst.get(b.id) ?? 0) - (worst.get(a.id) ?? 0))
    .slice(0, n);
}

export function heatRows(gaps: Schemas["GapHeatmapResponse"], skills: { id: string }[]) {
  const cell = new Map(gaps.cells.map((c) => [`${c.role_id}|${c.skill_id}`, c.gap]));
  return gaps.role_ids.map((r) => ({
    id: r,
    label: gaps.role_labels?.[r] ?? r,
    cells: skills.map((s) => ({ id: s.id, value: cell.get(`${r}|${s.id}`) ?? 0 })),
  }));
}

/** Organisation home: one next step (invite → wait → act), then status as visuals. */
export async function OrgDashboardView({ scenario }: { scenario: ScenarioId }) {
  const t = await getTranslations("ui.org");
  const tn = await getTranslations("ui.nav");
  const [org, members, gaps] = await Promise.all([fetchMyOrg(), fetchMembers(), fetchGaps(scenario)]);
  if (!org.ok) return <ErrorState failure={org} />;
  const list = members.ok ? members.data.members : [];
  const complete = list.filter((m) => m.intake_status === "complete").length;
  const [plan, impact] =
    complete > 0 ? await Promise.all([fetchPlan(scenario), fetchOrgContribution(scenario)]) : [null, null];

  const counts = {
    invited: list.filter((m) => m.intake_status === "invited").length,
    progress: list.filter((m) => m.intake_status === "in_progress").length,
    complete,
  };
  const skills = gaps.ok ? topGapSkills(gaps.data, 8) : [];
  const goals = impact?.ok
    ? impact.data.goals_summary
        .filter((g) => g.link_count > 0)
        .sort((a, b) => b.link_count - a.link_count)
        .slice(0, 6)
        .map((g) => ({ goal: g.goal, title: g.label, count: g.link_count }))
    : [];
  const steps = plan?.ok
    ? plan.data.steps.slice(0, 6).map((s, i) => ({
        id: s.skill_id,
        label: `${s.skill_label || s.skill_id} · ${(s.member_ids ?? []).length}`,
        state: i === 0 ? ("current" as const) : ("todo" as const),
      }))
    : [];

  return (
    <div className="a-stack">
      <section className="a-hero">
        <div>
          <span className="a-eyebrow">{org.data.name}</span>
          {list.length === 0 ? (
            <>
              <h1>{t("inviteTitle")}</h1>
              <p>{t("inviteBody")}</p>
              {org.data.join_code ? <JoinCodeCard code={org.data.join_code} /> : null}
            </>
          ) : complete === 0 ? (
            <>
              <h1>{t("waitTitle")}</h1>
              <p>{t("waitBody", { count: list.length })}</p>
              {org.data.join_code ? <JoinCodeCard code={org.data.join_code} /> : null}
            </>
          ) : (
            <>
              <h1>{t("readyTitle", { count: complete })}</h1>
              <p>{t("readyBody", { role: plan?.ok ? plan.data.target_role_label : "—" })}</p>
              <div className="a-hero-actions">
                <Link className="a-btn" href={`/org/gaps?scenario=${scenario}`}>
                  {t("readyCta")} <ArrowRight size={16} aria-hidden />
                </Link>
                <Link className="a-btn is-ghost" href={`/org/plan?scenario=${scenario}`}>
                  {t("planCta")}
                </Link>
              </div>
            </>
          )}
        </div>
        {complete > 0 ? (
          <div style={{ display: "grid", placeItems: "center" }}>
            <Ring value={list.length ? complete / list.length : 0} size={150} stroke={13} caption={t("complete")} colour="#6b6fd6" />
          </div>
        ) : (
          <Scene3D variant="grid" />
        )}
      </section>

      <div className="a-grid">
        <section className="a-card a-span-5" aria-labelledby="o-team">
          <div className="a-card-head">
            <h2 id="o-team">
              <Users size={16} aria-hidden style={{ verticalAlign: -3, marginRight: 6 }} />
              {t("intake")}
            </h2>
            <Link href="/org/members">
              {tn("team")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          <div className="a-stats" style={{ marginBottom: 14 }}>
            <div className="a-stat">
              <strong>{list.length}</strong>
              <span>{t("members")}</span>
            </div>
            <div className="a-stat">
              <strong>{complete}</strong>
              <span>{t("complete")}</span>
            </div>
          </div>
          <StackBar
            parts={[
              { key: "c", label: t("complete"), value: counts.complete, colour: "#2f8f5b" },
              { key: "p", label: t("inProgress"), value: counts.progress, colour: "#d48a26" },
              { key: "i", label: t("invited"), value: counts.invited, colour: "#c9cdc4" },
            ]}
          />
        </section>

        <section className="a-card a-span-7" aria-labelledby="o-gaps">
          <div className="a-card-head">
            <h2 id="o-gaps">
              <Grid3x3 size={16} aria-hidden style={{ verticalAlign: -3, marginRight: 6 }} />
              {t("gapsTitle")}
            </h2>
            <Link href={`/org/gaps?scenario=${scenario}`}>
              {tn("gaps")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {!gaps.ok ? (
            <ErrorState failure={gaps} compact />
          ) : skills.length ? (
            <Heatmap rows={heatRows(gaps.data, skills)} columns={skills.map((s) => ({ id: s.id, label: s.label }))} legend={[t("gapsLow"), t("gapsHigh")]} />
          ) : (
            <p className="a-muted a-small">{t("noGaps")}</p>
          )}
        </section>

        <section className="a-card a-span-7" aria-labelledby="o-plan">
          <div className="a-card-head">
            <h2 id="o-plan">
              <Route size={16} aria-hidden style={{ verticalAlign: -3, marginRight: 6 }} />
              {t("planTitle")}
              {plan?.ok ? <span className="a-chip" style={{ marginLeft: 10 }}>{plan.data.target_role_label}</span> : null}
            </h2>
            <Link href={`/org/plan?scenario=${scenario}`}>
              {tn("teamPlan")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {plan?.ok && steps.length ? (
            <>
              <StepTrack steps={steps} />
              <p className="a-small a-muted" style={{ marginBottom: 0 }}>
                {t("planBody", { steps: plan.data.steps.length, weeks: plan.data.total_weeks, people: plan.data.assigned_member_ids.length })}
              </p>
            </>
          ) : (
            <p className="a-muted a-small">{t("noGaps")}</p>
          )}
        </section>

        <section className="a-card a-span-5" aria-labelledby="o-impact">
          <div className="a-card-head">
            <h2 id="o-impact">
              <Leaf size={16} aria-hidden style={{ verticalAlign: -3, marginRight: 6 }} />
              {tn("impact")}
            </h2>
            <Link href={`/org/sdg?scenario=${scenario}`}>
              {tn("impact")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {goals.length ? <SdgTiles goals={goals} /> : <Scene3D variant="globe" />}
        </section>
      </div>
      {gaps.ok ? <MetaBar meta={gaps.data.meta} /> : null}
    </div>
  );
}
