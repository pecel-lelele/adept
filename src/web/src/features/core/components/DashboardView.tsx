import { ArrowRight, ArrowUpRight, BookOpen, Check, Compass, Leaf, Route, Target, TrendingUp } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { Kpis, MetaBar } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { ScoreBar, SdgTiles, StepTrack, TrendBars, type TrackStep, type TrendBar } from "@/components/viz";
import { fetchMatches } from "@/features/matching/api";
import { fetchPlanStatus, fetchProgress } from "@/features/pathway/api";
import { fetchMyProfile } from "@/features/profile/api";
import { fetchMyContribution } from "@/features/sdg/api";
import { fetchRadar } from "@/features/trends/api";
import type { ScenarioId } from "@/lib/api";
import { getAccount } from "@/lib/auth/account";
import { journeyHref } from "@/lib/navigation";

/**
 * Learner home. Hierarchy: one next action beside the four-step journey → four headline
 * numbers → top roles and the learner's skill trends → the plan and the goals it supports.
 * Charts and lists only; illustrations stay on the public pages.
 */
export async function DashboardView({ scenario, query }: { scenario: ScenarioId; query: URLSearchParams }) {
  const account = await getAccount();
  if (account && !account.has_profile) redirect("/app/onboarding");
  const t = await getTranslations("ui.home");
  const tp = await getTranslations("ui.page");
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

  const top = matches.ok ? matches.data.matches.slice(0, 4) : [];
  const best = top[0];
  const p = progress?.ok ? progress.data : null;
  const courses = p
    ? p.pathway.steps.flatMap((s) => s.courses).filter((c, i, all) => all.findIndex((x) => x.id === c.id) === i)
    : [];
  const done = p ? courses.filter((c) => p.course_status[c.id] === "completed").length : 0;
  const next = p ? courses.find((c) => p.course_status[c.id] !== "completed") : undefined;
  const planQuery = saved ? `?role=${encodeURIComponent(saved.role_id)}&scenario=${saved.scenario}` : "";

  // One next action.
  let hero: { title: string; body: string; cta: string; to: string };
  if (saved && next) {
    hero = {
      title: t("continueTitle", { course: next.title }),
      body: t("continueBody", { done, total: courses.length, role: saved.pathway.role_label }),
      cta: t("continueCta"),
      to: `/app/progress${planQuery}`,
    };
  } else if (saved && !p) {
    // Progress could not be read: never claim the path is complete.
    hero = { title: t("progressErrorTitle"), body: t("progressErrorBody"), cta: t("progressErrorCta"), to: `/app/progress${planQuery}` };
  } else if (saved) {
    hero = { title: t("doneTitle", { role: saved.pathway.role_label }), body: t("doneBody"), cta: t("doneCta"), to: `/app/progress${planQuery}` };
  } else {
    hero = {
      title: best ? t("chooseTitle", { role: best.label }) : t("startTitle"),
      body: best ? t("chooseBody") : t("startBody"),
      cta: best ? t("chooseCta") : t("startCta"),
      to: best ? href("/app/matches") : "/app/onboarding",
    };
  }

  // The four journey steps, done in order.
  const complete = p ? p.percent_complete >= 1 : false;
  const journeyDone = [Boolean(profile.ok && profile.data.skills.length), Boolean(saved), Boolean(saved), complete];
  const firstOpen = journeyDone.findIndex((d) => !d);
  const journey = [
    { key: "jSkills", to: "/app/profile" },
    { key: "jRadar", to: href("/app/radar") },
    { key: "jRoles", to: href("/app/matches") },
    { key: "jPlan", to: saved ? `/app/pathway${planQuery}` : href("/app/matches") },
  ] as const;

  // The learner's own skills on the radar: rising right, declining left.
  const velocity = scenario === "fast" ? "velocity_fast" : "velocity_moderate";
  const direction = scenario === "fast" ? "direction_fast" : "direction_moderate";
  const tracked = new Map(radar.ok ? radar.data.items.map((i) => [i.skill_id, i]) : []);
  const mine = profile.ok ? profile.data.skills : [];
  const mineTracked = mine.map((s) => tracked.get(s.skill_id)).filter((i): i is NonNullable<typeof i> => Boolean(i));
  const risingMine = mineTracked.filter((i) => i[direction] === "rising").length;
  const bars: TrendBar[] = mineTracked
    .map((i) => ({ id: i.skill_id, label: i.skill_label, value: i[velocity], direction: i[direction] }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 7);

  const isDone = (s: { courses: { id: string }[] }) =>
    Boolean(p && s.courses.length > 0 && s.courses.every((c) => p.course_status[c.id] === "completed"));
  const steps: TrackStep[] = saved
    ? saved.pathway.steps.slice(0, 6).map((s, i, all) => ({
        id: s.skill_id,
        label: s.skill_label || s.skill_id,
        state: isDone(s) ? "done" : i === all.findIndex((x) => !isDone(x)) ? "current" : "todo",
      }))
    : [];
  const linkedGoals = impact?.ok ? impact.data.goals_summary.filter((g) => g.link_count > 0).length : null;
  const goals = impact?.ok
    ? impact.data.goals_summary
        .filter((g) => g.link_count > 0)
        .sort((a, b) => b.link_count - a.link_count)
        .slice(0, 6)
        .map((g) => ({ goal: g.goal, title: g.label, count: g.link_count }))
    : [];

  return (
    <div className="a-view">
      <section className="a-welcome">
        <div className="a-welcome-main">
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
        <nav className="a-journey" aria-label={tp("journey")}>
          <span className="a-eyebrow">{tp("journey")}</span>
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
          {
            label: tp("kBestFit"),
            value: best ? `${Math.round(best.score * 100)}%` : "—",
            icon: <Compass size={15} />,
            note: best ? best.label : tp("kNone"),
          },
          {
            label: tp("kSkillsRising"),
            value: risingMine,
            icon: <TrendingUp size={15} />,
            tone: risingMine ? "up" : undefined,
            note: tp("kRisingNote", { count: mineTracked.length }),
          },
          {
            label: tp("kPlan"),
            value: p ? `${Math.round(p.percent_complete * 100)}%` : "—",
            icon: <Target size={15} />,
            note: p ? tp("kCoursesDone", { done, total: courses.length }) : tp("kPlanNone"),
          },
          {
            label: tp("kGoals"),
            value: linkedGoals ?? "—",
            icon: <Leaf size={15} />,
            note: linkedGoals === null ? tp("kPlanNone") : tp("kOf17"),
          },
        ]}
      />

      <div className="a-split">
        <section className="a-card" aria-labelledby="h-roles">
          <div className="a-card-head">
            <h2 id="h-roles">
              <Compass size={16} aria-hidden /> {t("topRoles")}
            </h2>
            <Link href={href("/app/matches")}>
              {t("seeAll")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {!matches.ok ? (
            <ErrorState failure={matches} compact />
          ) : (
            <ol className="a-rank">
              {top.map((m, i) => (
                <li key={m.role_id}>
                  <Link href={href(`/app/matches/${m.role_id}`)}>
                    <span className="a-rank-num">{i + 1}</span>
                    <span className="a-rank-main">
                      <strong>{m.label}</strong>
                      <small>{t("gaps", { count: m.missing_skills.length + m.partial_skills.length })}</small>
                    </span>
                    <ScoreBar value={m.score} label={t("fit")} />
                  </Link>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="a-card a-skill-trends" aria-labelledby="h-skills">
          <div className="a-card-head">
            <h2 id="h-skills">
              <TrendingUp size={16} aria-hidden /> {t("yourSkills")}
            </h2>
            <Link href={href("/app/radar")}>
              {t("seeAll")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {bars.length ? <TrendBars items={bars} /> : <p className="a-muted a-small">{t("yourSkillsEmpty")}</p>}
        </section>
      </div>

      <div className="a-split">
        <section className="a-card" aria-labelledby="h-path">
          <div className="a-card-head">
            <h2 id="h-path">
              <Route size={16} aria-hidden /> {t("path")}
            </h2>
            <Link href={saved ? `/app/pathway${planQuery}` : href("/app/matches")}>
              {t("seeAll")} <ArrowUpRight size={13} aria-hidden />
            </Link>
          </div>
          {saved ? (
            <div className="a-stack" style={{ gap: 18 }}>
              <p className="a-path-role">
                <strong>{saved.pathway.role_label}</strong>
                <span>{t("weeks", { weeks: saved.pathway.total_weeks })}</span>
              </p>
              <StepTrack steps={steps} />
              {next ? (
                <a className="a-course-row" href={next.url} target="_blank" rel="noreferrer">
                  <span className="a-course-icon" aria-hidden>
                    <BookOpen size={18} strokeWidth={1.6} />
                  </span>
                  <span className="a-course-main">
                    <small>{tp("upNext")}</small>
                    <strong>
                      {next.title} <ArrowUpRight size={13} aria-hidden />
                    </strong>
                  </span>
                </a>
              ) : null}
            </div>
          ) : (
            <p className="a-muted a-small">{t("noPath")}</p>
          )}
        </section>

        <section className="a-card" aria-labelledby="h-impact">
          <div className="a-card-head">
            <h2 id="h-impact">
              <Leaf size={16} aria-hidden /> {t("impact")}
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
