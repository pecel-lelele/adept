import { ArrowRight, ArrowUpRight, Compass, Leaf, Route } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import {
  Ring,
  RiseArt,
  Scene3D,
  scoreColour,
  SdgTiles,
  StepTrack,
  TrendBars,
  type TrackStep,
  type TrendBar,
} from "@/components/viz";
import { fetchMatches } from "@/features/matching/api";
import { fetchPlanStatus, fetchProgress } from "@/features/pathway/api";
import { fetchMyProfile } from "@/features/profile/api";
import { fetchMyContribution } from "@/features/sdg/api";
import { fetchRadar } from "@/features/trends/api";
import type { ScenarioId } from "@/lib/api";
import { getAccount } from "@/lib/auth/account";
import { journeyHref } from "@/lib/navigation";

/**
 * Learner home. Hierarchy: one "next step" hero → three role rings → how the learner's own
 * skills are trending → their path as a track → the goals it supports. Numbers become
 * visuals; detail lives one tap away.
 */
export async function DashboardView({ scenario, query }: { scenario: ScenarioId; query: URLSearchParams }) {
  const account = await getAccount();
  if (account && !account.has_profile) redirect("/app/onboarding");
  const t = await getTranslations("ui.home");
  const [profile, matches, status, radar] = await Promise.all([
    fetchMyProfile(),
    fetchMatches(scenario),
    fetchPlanStatus(),
    fetchRadar(scenario),
  ]);
  const saved = status.ok ? status.data.saved : null;
  const [progress, impact] = saved
    ? await Promise.all([
        fetchProgress(saved.role_id, saved.scenario as ScenarioId),
        fetchMyContribution(saved.role_id, saved.scenario as ScenarioId),
      ])
    : [null, null];
  const href = (path: string) => journeyHref(path, query);

  const top = matches.ok ? matches.data.matches.slice(0, 3) : [];
  const best = top[0];
  const p = progress?.ok ? progress.data : null;
  const courses = p
    ? p.pathway.steps.flatMap((s) => s.courses).filter((c, i, all) => all.findIndex((x) => x.id === c.id) === i)
    : [];
  const done = p ? courses.filter((c) => p.course_status[c.id] === "completed").length : 0;
  const next = p ? courses.find((c) => p.course_status[c.id] !== "completed") : undefined;
  const planQuery = saved ? `?role=${encodeURIComponent(saved.role_id)}&scenario=${saved.scenario}` : "";

  // Hero: exactly one next action.
  let hero: { title: string; body: string; cta: string; to: string; scene: "rise" | "cards" };
  if (saved && next) {
    hero = {
      title: t("continueTitle", { course: next.title }),
      body: t("continueBody", { done, total: courses.length, role: saved.pathway.role_label }),
      cta: t("continueCta"),
      to: `/app/progress${planQuery}`,
      scene: "rise",
    };
  } else if (saved && !p) {
    // Progress could not be read: never claim the path is complete. The progress page
    // shows the error with a retry.
    hero = {
      title: t("progressErrorTitle"),
      body: t("progressErrorBody"),
      cta: t("progressErrorCta"),
      to: `/app/progress${planQuery}`,
      scene: "rise",
    };
  } else if (saved) {
    hero = {
      title: t("doneTitle", { role: saved.pathway.role_label }),
      body: t("doneBody"),
      cta: t("doneCta"),
      to: `/app/progress${planQuery}`,
      scene: "rise",
    };
  } else {
    hero = {
      title: best ? t("chooseTitle", { role: best.label }) : t("startTitle"),
      body: best ? t("chooseBody") : t("startBody"),
      cta: best ? t("chooseCta") : t("startCta"),
      to: best ? href("/app/matches") : "/app/onboarding",
      scene: "cards",
    };
  }

  // The learner's own skills on the radar: rising right, declining left.
  const velocity = scenario === "fast" ? "velocity_fast" : "velocity_moderate";
  const direction = scenario === "fast" ? "direction_fast" : "direction_moderate";
  const tracked = new Map(radar.ok ? radar.data.items.map((i) => [i.skill_id, i]) : []);
  const mine = profile.ok ? profile.data.skills : [];
  const bars: TrendBar[] = mine
    .map((s) => tracked.get(s.skill_id))
    .filter((i): i is NonNullable<typeof i> => Boolean(i))
    .map((i) => ({ id: i.skill_id, label: i.skill_label, value: i[velocity], direction: i[direction] }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  const steps: TrackStep[] = saved
    ? saved.pathway.steps.slice(0, 6).map((s, i, all) => {
        const complete = p ? s.courses.length > 0 && s.courses.every((c) => p.course_status[c.id] === "completed") : false;
        const firstOpen = all.findIndex((x) => !(p && x.courses.length > 0 && x.courses.every((c) => p.course_status[c.id] === "completed")));
        return { id: s.skill_id, label: s.skill_label || s.skill_id, state: complete ? "done" : i === firstOpen ? "current" : "todo" };
      })
    : [];
  const goals = impact?.ok
    ? impact.data.goals_summary
        .filter((g) => g.link_count > 0)
        .sort((a, b) => b.link_count - a.link_count)
        .slice(0, 6)
        .map((g) => ({ goal: g.goal, title: g.label, count: g.link_count }))
    : [];

  return (
    <div className="a-stack">
      <section className="a-hero">
        <div>
          <span className="a-eyebrow">{t("hello", { name: account?.display_name ?? "" })}</span>
          <h1>{hero.title}</h1>
          <p>{hero.body}</p>
          <div className="a-hero-actions">
            <Link className="a-btn" href={hero.to}>
              {hero.cta} <ArrowRight size={16} aria-hidden />
            </Link>
            {status.ok && status.data.needs_replan ? (
              <Link className="a-chip" data-tone="warn" href={`/app/pathway${planQuery}`}>
                {t("replan")} {t("review")}
              </Link>
            ) : null}
          </div>
        </div>
        {p ? (
          <div style={{ display: "grid", placeItems: "center", gap: 12 }}>
            <Ring value={p.percent_complete} size={150} stroke={13} caption={t("progress")} colour="var(--a-up)" />
            <div className="a-chips" style={{ justifyContent: "center" }}>
              <span className="a-chip">{t("badges")} · {p.badges.length}</span>
              <span className="a-chip">{t("gap")} · {p.gap_closed}/{p.gap_total}</span>
            </div>
          </div>
        ) : hero.scene === "rise" ? (
          <RiseArt />
        ) : (
          <Scene3D variant="cards" />
        )}
      </section>

      <div className="a-grid">
        <section className="a-card a-span-7" aria-labelledby="h-roles">
          <div className="a-card-head">
            <h2 id="h-roles">
              <Compass size={16} aria-hidden style={{ verticalAlign: -3, marginRight: 6 }} />
              {t("topRoles")}
            </h2>
            <Link href={href("/app/matches")}>
              {t("seeAll")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {!matches.ok ? (
            <ErrorState failure={matches} compact />
          ) : (
            <div className="a-roles">
              {top.map((m) => (
                <Link key={m.role_id} className="a-role" href={href(`/app/matches/${m.role_id}`)}>
                  <Ring value={m.score} size={84} stroke={8} caption={t("fit")} colour={scoreColour(m.score)} />
                  <h3>{m.label}</h3>
                  <span className="a-chip" data-tone={m.missing_skills.length ? "warn" : "up"}>
                    {t("gaps", { count: m.missing_skills.length + m.partial_skills.length })}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="a-card a-span-5" aria-labelledby="h-skills">
          <div className="a-card-head">
            <h2 id="h-skills">{t("yourSkills")}</h2>
            <Link href={href("/app/radar")}>
              {t("seeAll")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {bars.length ? <TrendBars items={bars} /> : <p className="a-muted a-small">{t("yourSkillsEmpty")}</p>}
        </section>

        <section className="a-card a-span-7" aria-labelledby="h-path">
          <div className="a-card-head">
            <h2 id="h-path">
              <Route size={16} aria-hidden style={{ verticalAlign: -3, marginRight: 6 }} />
              {t("path")}
              {saved ? <span className="a-chip" style={{ marginLeft: 10 }}>{saved.pathway.role_label} · {t("weeks", { weeks: saved.pathway.total_weeks })}</span> : null}
            </h2>
            <Link href={saved ? `/app/pathway${planQuery}` : href("/app/matches")}>
              {t("seeAll")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {steps.length ? <StepTrack steps={steps} /> : <p className="a-muted a-small">{t("noPath")}</p>}
        </section>

        <section className="a-card a-span-5" aria-labelledby="h-impact">
          <div className="a-card-head">
            <h2 id="h-impact">
              <Leaf size={16} aria-hidden style={{ verticalAlign: -3, marginRight: 6 }} />
              {t("impact")}
            </h2>
            <Link href={`/app/sdg${planQuery}`}>
              {t("seeAll")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {goals.length ? <SdgTiles goals={goals} /> : <p className="a-muted a-small">{t("noImpact")}</p>}
        </section>
      </div>
      {matches.ok ? <MetaBar meta={matches.data.meta} /> : null}
    </div>
  );
}
