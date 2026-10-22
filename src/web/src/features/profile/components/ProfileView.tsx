import { ArrowRight, Building2, Clock3, Layers, Pencil, TrendingUp, Wallet } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { Kpis, PageHeader, TrendPill } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { LevelPips } from "@/components/viz";
import { fetchMyOrg } from "@/features/org/api";
import { fetchRadar } from "@/features/trends/api";
import type { ScenarioId } from "@/lib/api";

import { fetchMyProfile, fetchSkillCatalogue } from "../api";

/**
 * Step 1 result. Hierarchy: the four numbers that shape the plan → every confirmed skill as a
 * row (level and demand trend in words) → who the learner is, and the next step.
 */
export async function ProfileView({ scenario = "moderate" }: { scenario?: ScenarioId }) {
  const t = await getTranslations("ui.skills");
  const tp = await getTranslations("ui.page");
  const ti = await getTranslations("ui.intake");
  const tj = await getTranslations("ui.join");
  const [profile, catalogue, radar, org] = await Promise.all([
    fetchMyProfile(),
    fetchSkillCatalogue(),
    fetchRadar(scenario),
    fetchMyOrg(),
  ]);
  if (!profile.ok) return <ErrorState failure={profile} />;
  const p = profile.data;
  const labels = new Map(catalogue.ok ? catalogue.data.skills.map((s) => [s.id, s.label]) : []);
  const trend = new Map(radar.ok ? radar.data.items.map((i) => [i.skill_id, scenario === "fast" ? i.direction_fast : i.direction_moderate]) : []);
  const skills = [...p.skills].sort((a, b) => b.level - a.level || a.skill_id.localeCompare(b.skill_id));
  const tracked = skills.filter((s) => trend.has(s.skill_id));
  const rising = tracked.filter((s) => trend.get(s.skill_id) === "rising").length;

  return (
    <div className="a-view">
      <PageHeader
        eyebrow={tp("stepOf", { step: 1 })}
        title={t("title")}
        description={tp("skillsDesc")}
        actions={
          <Link className="a-btn is-ghost" href="/app/onboarding">
            <Pencil size={15} aria-hidden /> {t("edit")}
          </Link>
        }
      />

      <Kpis
        items={[
          { label: tp("kSkills"), value: skills.length, icon: <Layers size={15} /> },
          {
            label: tp("kRising"),
            value: rising,
            icon: <TrendingUp size={15} />,
            tone: rising ? "up" : undefined,
            note: tp("kRisingNote", { count: tracked.length }),
          },
          { label: tp("kTime"), value: p.hours_per_week, unit: tp("hPerWeek"), icon: <Clock3 size={15} /> },
          {
            label: tp("kBudget"),
            value: `RM ${p.budget_myr.toLocaleString("en-MY")}`,
            icon: <Wallet size={15} />,
            note: p.hrd_eligible ? tp("hrdYes") : tp("hrdNo"),
          },
        ]}
      />

      <div className="a-split">
        <section className="a-card a-flush" aria-labelledby="h-levels">
          <div className="a-card-head a-pad">
            <h2 id="h-levels">{tp("skillLevels")}</h2>
            <span className="a-muted a-small">{tp("trendSource", { date: radar.ok ? radar.data.meta.snapshot_date : "—" })}</span>
          </div>
          <table className="a-table">
            <thead>
              <tr>
                <th scope="col">{tp("colSkill")}</th>
                <th scope="col">{tp("colLevel")}</th>
                <th scope="col">{tp("colTrend")}</th>
              </tr>
            </thead>
            <tbody>
              {skills.map((s) => (
                <tr key={s.skill_id}>
                  <th scope="row">{labels.get(s.skill_id) ?? s.skill_id}</th>
                  <td>
                    <span className="a-level">
                      <LevelPips level={s.level} label={t("level", { level: s.level })} />
                      <span>{tp(`level${Math.min(5, Math.max(1, s.level))}` as "level1")}</span>
                    </span>
                  </td>
                  <td>
                    <TrendPill direction={trend.get(s.skill_id)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <aside className="a-aside">
          <section className="a-card" aria-labelledby="h-about">
            <div className="a-card-head">
              <h2 id="h-about">{tp("aboutYou")}</h2>
            </div>
            <dl className="a-dl">
              <div>
                <dt>{tp("stage")}</dt>
                <dd>{ti(p.segment)}</dd>
              </div>
              <div>
                <dt>{tp("learningStyle")}</dt>
                <dd>{ti(`style.${p.learning_style ?? "mixed"}`)}</dd>
              </div>
              <div>
                <dt>{tp("interests")}</dt>
                <dd>
                  {p.interests?.length ? (
                    <span className="a-chips">
                      {p.interests.map((i) => (
                        <span className="a-chip" key={i}>
                          {i}
                        </span>
                      ))}
                    </span>
                  ) : (
                    <span className="a-muted">{tp("none")}</span>
                  )}
                </dd>
              </div>
              <div>
                <dt>{tp("organisation")}</dt>
                <dd>
                  {org.ok ? (
                    <span className="a-inline">
                      <Building2 size={14} aria-hidden /> {org.data.name}
                    </span>
                  ) : (
                    <Link className="a-link" href="/app/join">
                      {tj("title")} <ArrowRight size={13} aria-hidden />
                    </Link>
                  )}
                </dd>
              </div>
            </dl>
          </section>

          <Link className="a-card a-next" href="/app/radar">
            <span className="a-eyebrow">{tp("nextStep")}</span>
            <strong>{tp("nextRadarTitle")}</strong>
            <span>{tp("nextRadarBody")}</span>
            <span className="a-next-go">
              {tp("openRadar")} <ArrowRight size={15} aria-hidden />
            </span>
          </Link>
        </aside>
      </div>
    </div>
  );
}
