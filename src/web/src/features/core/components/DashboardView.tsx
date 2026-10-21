import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { fetchPlanStatus, fetchProgress } from "@/features/pathway/api";
import { fetchMembers, fetchMyOrg } from "@/features/org/api";
import { MetaBar } from "@/components";
import { journeyHref } from "@/lib/navigation";
import { DepthArt } from "./DepthArt";

export async function DashboardView({
  mode,
  query,
}: {
  mode: "individual" | "organisation";
  query: URLSearchParams;
}) {
  const t = await getTranslations("common.workspace"),
    org = mode === "organisation";
  const status = !org ? await fetchPlanStatus() : null;
  const saved = status?.ok ? status.data.saved : null;
  if (saved && !query.has("role")) query.set("role", saved.role_id);
  const href = (route: string) => journeyHref(route, query);
  const progress = saved
    ? await fetchProgress(
        saved.role_id,
        query.get("scenario") === "fast" ? "fast" : "moderate",
      )
    : null;
  const p = progress?.ok ? progress.data : null;
  const [company, members] = org
    ? await Promise.all([fetchMyOrg(), fetchMembers()])
    : [null, null];
  const cards = org
    ? ([
        ["/org/members", "membersTitle", "membersBody"],
        ["/org/gaps", "gapsTitle", "gapsBody"],
        ["/org/plan", "planTitle", "planBody"],
        ["/org/verify", "verifyTitle", "verifyBody"],
        ["/org/courses", "coursesTitle", "coursesBody"],
        ["/org/sdg", "impactTitle", "impactBody"],
      ] as const)
    : ([
        ["/app/profile", "profileTitle", "profileBody"],
        ["/app/radar", "radarTitle", "radarBody"],
        ["/app/matches", "matchesTitle", "matchesBody"],
        ["/app/pathway/compare", "compareTitle", "compareBody"],
        ["/app/courses", "coursesTitle", "coursesBody"],
        ["/app/sdg", "impactTitle", "impactBody"],
      ] as const);
  const courses = p
    ? p.pathway.steps
        .flatMap((s) => s.courses)
        .filter((c, i, all) => all.findIndex((x) => x.id === c.id) === i)
    : [];
  const completed = p
    ? courses.filter((c) => p.course_status[c.id] === "completed").length
    : 0;
  const points = completed * 100;
  const unavailable = org
    ? company?.ok === false || members?.ok === false
    : status?.ok === false;
  return (
    <section className="dashboard">
      <div className="dashboard-heading">
        <div>
          <p className="workspace-eyebrow">
            {t(org ? "orgEyebrow" : "learnerEyebrow")}
          </p>
          <h1>{t(org ? "orgTitle" : "learnerTitle")}</h1>
          <p>
            {company?.ok
              ? company.data.name
              : t(org ? "orgBody" : "learnerBody")}
          </p>
        </div>
        <Link
          className="workspace-button subtle"
          href={href(org ? "/org/setup" : "/app/profile")}
        >
          {t(org ? "manage" : "editProfile")} ↗
        </Link>
      </div>
      {unavailable ? (
        <p role="status" className="workspace-notice">
          {t("unavailable")}
        </p>
      ) : null}
      <div className="dashboard-bento">
        <article className="dashboard-hero">
          <div>
            <span className="hero-label">
              {t(org ? "orgHeroLabel" : "heroLabel")}
            </span>
            <h2>
              {t(org ? "orgHeroTitle" : saved ? "continueTitle" : "heroTitle")}
            </h2>
            <p>{t(org ? "orgHeroBody" : "heroBody")}</p>
            <Link
              className="workspace-button"
              href={href(
                org
                  ? "/org/gaps"
                  : saved
                    ? "/app/progress"
                    : "/app/pathway/compare",
              )}
            >
              {t(org ? "reviewGaps" : saved ? "continue" : "chooseRole")} →
            </Link>
          </div>
          <DepthArt variant={org ? "people" : "steps"} />
        </article>
        <article className="dashboard-metric">
          <span className="workspace-eyebrow">
            {t(org ? "team" : "learningProgress")}
          </span>
          <strong>
            {org
              ? members?.ok
                ? members.data.members.length
                : "—"
              : p
                ? Math.round(p.percent_complete * 100) + "%"
                : "—"}
          </strong>
          <p>{t(org ? "membersInDemo" : "savedPlanProgress")}</p>
          {p ? (
            <progress
              max={1}
              value={p.percent_complete}
              aria-label={t("learningProgress")}
            />
          ) : null}
          <Link href={href(org ? "/org/members" : "/app/pathway")}>
            {t(org ? "viewMembers" : "viewPlan")} ↗
          </Link>
        </article>
      </div>
      {!org ? (
        <div className="learning-strip">
          <div>
            <span className="workspace-eyebrow">{t("points")}</span>
            <strong>{points}</strong>
            <small>{t("pointsRule")}</small>
          </div>
          <div>
            <span className="workspace-eyebrow">{t("level")}</span>
            <strong>{1 + Math.floor(points / 500)}</strong>
            <small>{t("levelRule")}</small>
          </div>
          <div>
            <span className="workspace-eyebrow">{t("badges")}</span>
            <strong>{p?.badges.length ?? 0}</strong>
            <small>{t("badgesRule")}</small>
          </div>
        </div>
      ) : null}
      {p && courses.length ? (
        <article className="dashboard-resume">
          <div>
            <span className="workspace-eyebrow">{t("nextLesson")}</span>
            <h2>
              {courses.find((c) => p.course_status[c.id] !== "completed")
                ?.title ?? t("allDone")}
            </h2>
          </div>
          <Link
            className="workspace-button subtle"
            href={href("/app/progress")}
          >
            {t("openLearning")} →
          </Link>
        </article>
      ) : null}
      <div className="dashboard-section-heading">
        <h2>{t(org ? "teamWorkspace" : "explore")}</h2>
        <span>{t("connected")}</span>
      </div>
      <div className="dashboard-grid">
        {cards.map(([route, title, body], i) => (
          <Link key={route} className="dashboard-feature" href={href(route)}>
            <span className="feature-index">
              {String(i + 1).padStart(2, "0")}
            </span>
            <h3>{t(title)}</h3>
            <p>{t(body)}</p>
            <span className="feature-arrow" aria-hidden>
              ↗
            </span>
          </Link>
        ))}
      </div>
      {p ? <MetaBar meta={p.meta} /> : null}
    </section>
  );
}
