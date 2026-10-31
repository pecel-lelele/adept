import { AdminTrendRefresh } from "@/features/trends/components/AdminTrendRefresh";
import { ArrowRight, ArrowUpRight, Check, Grid3x3, Leaf, Route, Target, UserCheck, Users } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { Kpis } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { Heatmap, SdgTiles, StackBar, StepTrack } from "@/components/viz";
import { fetchOrgContribution } from "@/features/sdg/api";
import { SdgLinkCards } from "@/features/sdg/components/SdgLinkCards";
import { fetchProgrammes } from "../programmes/api";
import type { ScenarioId, Schemas } from "@/lib/api";

import { fetchGaps, fetchMembers, fetchMyOrg, fetchPlan } from "../api";
import { JoinCodeCard } from "./JoinCodeCard";
import { TeamLearningProgress } from "./TeamLearningProgress";

/** The most useful columns of a heatmap: skills with the largest gap anywhere, max `n`. */
export function topGapSkills(gaps: Schemas["GapHeatmapResponse"], n: number) {
  if (gaps.cells.some((c) => c.suppressed)) return gaps.skills.slice(0, n);
  const worst = new Map<string, number>();
  for (const c of gaps.cells) if (c.gap != null && !c.suppressed) worst.set(c.skill_id, Math.max(worst.get(c.skill_id) ?? 0, c.gap));
  return gaps.skills
    .filter((s) => (worst.get(s.id) ?? 0) > 0)
    .sort((a, b) => (worst.get(b.id) ?? 0) - (worst.get(a.id) ?? 0))
    .slice(0, n);
}

export function heatRows(gaps: Schemas["GapHeatmapResponse"], skills: { id: string }[]) {
  const cell = new Map(gaps.cells.map((c) => [`${c.role_id}|${c.skill_id}`, c]));
  return gaps.role_ids.map((r) => ({
    id: r,
    label: gaps.role_labels?.[r] ?? r,
    cells: skills.map((s) => {
      const entry = cell.get(`${r}|${s.id}`);
      return { id: s.id, value: entry?.gap ?? null, suppressed: entry?.suppressed ?? true };
    }),
  }));
}

/**
 * Organisation home, same rhythm as the learner pages: one next action beside the four-step
 * team journey → four headline numbers → where the team is short (heatmap) beside profile
 * status → the team plan beside the goals it supports. Every figure comes from the API.
 */
export async function OrgDashboardView({ scenario }: { scenario: ScenarioId }) {
  const t = await getTranslations("ui.org");
  const tn = await getTranslations("ui.nav");
  const tp = await getTranslations("ui.page");
  const [org, members, gaps, programmes] = await Promise.all([fetchMyOrg(), fetchMembers(), fetchGaps(scenario), fetchProgrammes()]);
  if (!org.ok) return <ErrorState failure={org} />;
  const list = members.ok ? members.data.members : [];
  const complete = list.filter((m) => m.intake_status === "complete").length;
  const [plan, impact] =
    complete > 0 ? await Promise.all([fetchPlan(scenario), fetchOrgContribution(scenario)]) : [null, null];
  const target = plan?.ok ? plan.data.target_role_id : undefined;
  const roleQuery = target ? `&role=${encodeURIComponent(target)}` : "";

  const counts = {
    invited: list.filter((m) => m.intake_status === "invited").length,
    progress: list.filter((m) => m.intake_status === "in_progress").length,
    complete,
  };
  const skills = gaps.ok ? topGapSkills(gaps.data, 8) : [];
  // Required skills only (from the API), so this matches how the backend picked the target.
  const avgGap = gaps.ok && target ? (gaps.data.role_gaps?.[target] ?? null) : null;
  const linkedGoals = impact?.ok ? impact.data.goals_summary.filter((g) => g.link_count > 0) : [];
  const goals = [...linkedGoals]
    .sort((a, b) => b.link_count - a.link_count)
    .slice(0, 6)
    .map((g) => ({ goal: g.goal, title: g.label, count: g.link_count }));
  const spotlight = impact?.ok ? impact.data.links.find((link) => link.target.goal === goals[0]?.goal) : null;
  const sdgLabels = new Map<string, string>([
    ...(plan?.ok && plan.data.target_role_id ? [[`role:${plan.data.target_role_id}`, plan.data.target_role_label] as const] : []),
    ...(gaps.ok ? gaps.data.skills.map((skill) => [`skill:${skill.id}`, skill.label] as const) : []),
  ]);
  const steps = plan?.ok
    ? plan.data.steps.slice(0, 6).map((s, i) => ({
        id: s.skill_id,
        label: `${s.skill_label || s.skill_id} · ${(s.member_ids ?? []).length}`,
        state: i === 0 ? ("current" as const) : ("todo" as const),
      }))
    : [];

  const journeyDone = [list.length > 0, complete > 0, complete > 0, Boolean(programmes.ok && programmes.data.programmes.length)];
  const firstOpen = journeyDone.findIndex((d) => !d);
  const journey = [
    { key: "oInvite", to: "/org/members" },
    { key: "oProfiles", to: `/org/radar?scenario=${scenario}` },
    { key: "oGaps", to: `/org/gaps?scenario=${scenario}` },
    { key: "oPlan", to: `/org/programmes?scenario=${scenario}${roleQuery}` },
  ] as const;

  return (
    <div className="a-view">
      <AdminTrendRefresh />
      <section className="a-welcome">
        <div className="a-welcome-main">
          <span className="a-eyebrow">{org.data.name}</span>
          {list.length === 0 ? (
            <>
              <h1>{t("inviteTitle")}</h1>
              <p>{t("inviteBody")}</p>
              {org.data.join_code ? <JoinCodeCard code={org.data.join_code} orgId={org.data.id} /> : null}
            </>
          ) : complete === 0 ? (
            <>
              <h1>{t("waitTitle")}</h1>
              <p>{t("waitBody", { count: list.length })}</p>
              {org.data.join_code ? <JoinCodeCard code={org.data.join_code} orgId={org.data.id} /> : null}
            </>
          ) : (
            <>
              <h1>{t("readyTitle", { count: complete })}</h1>
              <p>{t("readyBody", { role: plan?.ok ? plan.data.target_role_label : "—" })}</p>
              <div className="a-hero-actions">
                <Link className="a-btn" href={`/org/gaps?scenario=${scenario}`}>
                  {t("readyCta")} <ArrowRight size={16} aria-hidden />
                </Link>
                <Link className="a-btn is-ghost" href={`/org/plan?scenario=${scenario}${roleQuery}`}>
                  {t("planCta")}
                </Link>
              </div>
            </>
          )}
        </div>
        <nav className="a-journey" aria-label={tp("teamJourney")}>
          <span className="a-eyebrow">{tp("teamJourney")}</span>
          <ol>
            {journey.map((j, i) => {
              const state = journeyDone[i] ? "done" : i === firstOpen ? "current" : "todo";
              return (
                <li key={j.key} data-state={state}>
                  <Link href={j.to}>
                    <span className="a-journey-dot" aria-hidden>
                      {state === "done" ? <Check size={13} strokeWidth={3} /> : i + 1}
                    </span>
                    <span>{tp(j.key)}</span>
                    <span className="a-sr">{tp(`state.${state}`)}</span>
                    <ArrowUpRight size={14} className="a-journey-go" aria-hidden />
                  </Link>
                </li>
              );
            })}
          </ol>
        </nav>
      </section>

      <Kpis
        items={[
          { label: t("members"), value: list.length, icon: <Users size={15} />, note: tp("kInvitedNote", { count: counts.invited }) },
          {
            label: tp("kProfiles"),
            value: list.length ? `${Math.round((complete / list.length) * 100)}%` : "—",
            icon: <UserCheck size={15} />,
            tone: complete > 0 && complete === list.length ? "up" : undefined,
            note: tp("kProfilesNote", { done: complete, total: list.length }),
          },
          {
            label: tp("kTargetGap"),
            value: avgGap === null ? "—" : `${Math.round(avgGap * 100)}%`,
            icon: <Target size={15} />,
            tone: avgGap !== null && avgGap > 0.5 ? "warn" : undefined,
            note: plan?.ok ? plan.data.target_role_label : tp("kAfterProfiles"),
          },
          {
            label: tp("kGoals"),
            value: impact?.ok ? linkedGoals.length : "—",
            icon: <Leaf size={15} />,
            note: impact?.ok ? tp("kOf17") : tp("kAfterProfiles"),
          },
        ]}
      />

      <div className="a-split">
        <section className="a-card" aria-labelledby="o-gaps">
          <div className="a-card-head">
            <h2 id="o-gaps">
              <Grid3x3 size={16} aria-hidden /> {t("gapsTitle")}
            </h2>
            <Link href={`/org/gaps?scenario=${scenario}`}>
              {tn("gaps")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {gaps.ok && Object.values(gaps.data.role_suppressed ?? {}).some(Boolean) ? <p className="a-muted" role="status">{t("tooFewMembers")}</p> : null}
          {!gaps.ok ? (
            <ErrorState failure={gaps} compact />
          ) : skills.length ? (
            <Heatmap
              rows={heatRows(gaps.data, skills)}
              columns={skills.map((s) => ({ id: s.id, label: s.label }))}
              legend={[t("gapsLow"), t("gapsHigh")]}
              suppressedLabel={t("tooFewMembers")}
            />
          ) : (
            <p className="a-muted a-small">{t("noGaps")}</p>
          )}
        </section>

        <section className="a-card" aria-labelledby="o-team">
          <div className="a-card-head">
            <h2 id="o-team">
              <Users size={16} aria-hidden /> {t("intake")}
            </h2>
            <Link href="/org/members">
              {tn("team")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          <StackBar
            parts={[
              { key: "c", label: t("complete"), value: counts.complete, colour: "var(--a-up)" },
              { key: "p", label: t("inProgress"), value: counts.progress, colour: "var(--a-warn)" },
              { key: "i", label: t("invited"), value: counts.invited, colour: "#c9cdc4" },
            ]}
          />
        </section>
      </div>

      <div className="a-split">
        <section className="a-card" aria-labelledby="o-plan">
          <div className="a-card-head">
            <h2 id="o-plan">
              <Route size={16} aria-hidden /> {t("planTitle")}
            </h2>
            <Link href={`/org/plan?scenario=${scenario}${roleQuery}`}>
              {tn("teamPlan")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {plan?.ok && steps.length ? (
            <div className="a-stack" style={{ gap: 18 }}>
              <p className="a-path-role">
                <strong>{plan.data.target_role_label}</strong>
                <span>
                  {t("planBody", {
                    steps: plan.data.steps.length,
                    weeks: plan.data.total_weeks,
                    people: plan.data.assigned_member_ids.length,
                  })}
                </span>
              </p>
              <StepTrack steps={steps} />
            </div>
          ) : (
            <p className="a-muted a-small">{t("noGaps")}</p>
          )}
        </section>

        <section className="a-card" aria-labelledby="o-impact">
          <div className="a-card-head">
            <h2 id="o-impact">
              <Leaf size={16} aria-hidden /> {tn("impact")}
            </h2>
            <Link href={`/org/sdg?scenario=${scenario}${roleQuery}`}>
              {tn("impact")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {spotlight ? <div className="a-home-sdg-card"><SdgLinkCards links={[spotlight]} labels={sdgLabels} /></div> : goals.length ? <SdgTiles goals={goals} /> : <p className="a-muted a-small">{t("noGaps")}</p>}
        </section>
      </div>
      {gaps.ok ? <TeamLearningProgress rows={gaps.data.learning_progress ?? []} /> : null}
    </div>
  );
}
