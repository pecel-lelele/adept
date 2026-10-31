import { ArrowUpRight } from "lucide-react";
import { getTranslations } from "next-intl/server";

import type { Schemas } from "@/lib/api";

/** Soft rounded pills with a status dot (green: you have it, amber: in your plan, grey: to learn). */
export async function SkillPills({ skills, max = 6 }: { skills: Schemas["SkillAsk"][]; max?: number }) {
  const t = await getTranslations("jobs.status");
  if (!skills.length) return null;
  return (
    <ul className="a-pills">
      {skills.slice(0, max).map((s) => (
        <li key={s.skill_id} className="a-pill" data-status={s.status} title={t(s.status)}>
          <i aria-hidden />
          {s.label}
          <span className="a-sr">({t(s.status)})</span>
        </li>
      ))}
    </ul>
  );
}

/** What the dot colours mean, once per section. */
export async function StatusLegend() {
  const t = await getTranslations("jobs.status");
  return (
    <p className="a-legend">
      {(["have", "in_plan", "missing"] as const).map((s) => (
        <span key={s} data-status={s}>
          <i aria-hidden /> {t(s)}
        </span>
      ))}
    </p>
  );
}

/** The share of the job's listed skills the person has: today, and with the plan if it adds any. */
async function MatchBox({ now, after }: { now: number; after: number | null }) {
  const t = await getTranslations("jobs.match");
  return (
    <div className="a-match" role="group" aria-label={t("label")}>
      {after == null ? (
        <div className="a-match-row is-main">
          <span>{t("label")}</span>
          <strong data-zero={now === 0 || undefined}>{now}%</strong>
        </div>
      ) : (
        <>
          <div className="a-match-row">
            <span>{t("today")}</span>
            <strong>{now}%</strong>
          </div>
          <div className="a-match-row is-main">
            <span>{t("withPlan")}</span>
            <strong>{after}%</strong>
          </div>
        </>
      )}
      <span className="a-match-bar" aria-hidden>
        <i style={{ width: `${after ?? now}%` }} data-kind="plan" />
        <i style={{ width: `${now}%` }} />
      </span>
    </div>
  );
}

/** Open ads split by how they relate to Malaysia; empty remote parts are left out. */
export async function placeCounts(places: Schemas["OpeningPlaceCounts"]) {
  const t = await getTranslations("jobs.places");
  return [
    t("inMalaysia", { count: places.in_malaysia }),
    places.remote_explicit_my ? t("remoteOpen", { count: places.remote_explicit_my }) : null,
    places.remote_assumed_worldwide ? t("remoteWorldwide", { count: places.remote_assumed_worldwide }) : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

const RELEVANCE_TONE = {
  in_malaysia: "up",
  remote_explicit_my: undefined,
  remote_assumed_worldwide: "warn",
} as const;

/** One job: the employer link, work location, a bounded skill gap and an optional skill match. */
export async function OpeningItem({
  o,
  showFit = true,
  malaysiaFocus = false,
}: {
  o: Schemas["JobOpening"];
  showFit?: boolean;
  malaysiaFocus?: boolean;
}) {
  const t = await getTranslations("jobs");
  const place = malaysiaFocus
    ? o.location
    : o.work_mode === "remote"
      ? t("remote", { scope: o.remote_scope || t("anywhere") })
      : o.location || t("malaysia");
  const pct = (v: number | null | undefined) => (v == null ? null : Math.round(v * 100));
  const now = pct(o.match_now);
  const after = pct(o.match_after_plan);
  const toLearn = o.skills.filter((s) => s.status === "missing").slice(0, 3);
  return (
    <li className="a-job a-opening" data-stale={o.is_stale || undefined}>
      <div className="a-job-main">
        <div className="a-opening-top">
          <a className="a-job-title" href={o.url} target="_blank" rel="noopener noreferrer">
            {o.title}<ArrowUpRight size={16} aria-hidden />
          </a>
          {malaysiaFocus ? <span className="a-chip" data-tone={RELEVANCE_TONE[o.malaysia_relevance]}>{t(`relevance.${o.malaysia_relevance}`)}</span> : null}
        </div>
        <span className="a-job-where">{place ? `${o.employer} · ${place}` : o.employer}</span>
        {o.is_stale ? <span className="a-job-stale a-small a-muted" role="note">{t("stale", { date: o.last_seen })}</span> : null}
        {showFit && toLearn.length ? (
          <div className="a-opening-learning">
            <span>{t("status.missing")}</span>
            <ul>{toLearn.map((skill) => <li key={skill.skill_id}>{skill.label}</li>)}</ul>
          </div>
        ) : null}
      </div>
      {showFit && now != null ? <MatchBox now={now} after={after != null && after > now ? after : null} /> : null}
    </li>
  );
}
