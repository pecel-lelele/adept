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

/** One job: title (links to the employer's ad), company and place, what is left to learn, match. */
export async function OpeningItem({ o, showFit = true }: { o: Schemas["JobOpening"]; showFit?: boolean }) {
  const t = await getTranslations("jobs");
  const place =
    o.work_mode === "remote" ? t("remote", { scope: o.remote_scope || t("anywhere") }) : o.location || t("malaysia");
  const pct = (v: number | null | undefined) => (v == null ? null : Math.round(v * 100));
  const now = pct(o.match_now);
  const after = pct(o.match_after_plan);
  const toLearn = o.skills.filter((s) => s.status === "missing").map((s) => s.label);
  return (
    <li className="a-job">
      <div className="a-job-main">
        <a className="a-job-title" href={o.url} target="_blank" rel="noopener">
          {o.title}
          <ArrowUpRight size={14} aria-hidden />
        </a>
        <span className="a-job-where">
          {o.employer}, {place}
        </span>
        {showFit && toLearn.length ? (
          <span className="a-job-learn">{t("toLearn", { skills: toLearn.slice(0, 3).join(", ") })}</span>
        ) : null}
      </div>
      {showFit && now != null ? <MatchBox now={now} after={after != null && after > now ? after : null} /> : null}
    </li>
  );
}
