import { Building2, Pencil } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ErrorState } from "@/components/ErrorState";
import { RiseArt } from "@/components/viz";
import { fetchMyOrg } from "@/features/org/api";
import { fetchRadar } from "@/features/trends/api";

import { fetchMyProfile, fetchSkillCatalogue } from "../api";

/** Step 1 result: the learner's confirmed skills as level bars, each with its trend. */
export async function ProfileView() {
  const t = await getTranslations("ui.skills");
  const ti = await getTranslations("ui.intake");
  const tj = await getTranslations("ui.join");
  const [profile, catalogue, radar, org] = await Promise.all([
    fetchMyProfile(),
    fetchSkillCatalogue(),
    fetchRadar("moderate"),
    fetchMyOrg(),
  ]);
  if (!profile.ok) return <ErrorState failure={profile} />;
  const p = profile.data;
  const labels = new Map(catalogue.ok ? catalogue.data.skills.map((s) => [s.id, s.label]) : []);
  const trend = new Map(radar.ok ? radar.data.items.map((i) => [i.skill_id, i]) : []);
  const skills = [...p.skills].sort((a, b) => b.level - a.level);

  return (
    <div className="a-stack">
      <div className="a-pagehead">
        <div>
          <span className="a-eyebrow">{ti(p.segment)}</span>
          <h1 className="a-h1">{t("title")}</h1>
        </div>
        <Link className="a-btn" href="/app/onboarding">
          <Pencil size={15} aria-hidden /> {t("edit")}
        </Link>
      </div>
      <div className="a-grid">
        <section className="a-card a-span-8">
          <div className="a-bars">
            {skills.map((s) => {
              const item = trend.get(s.skill_id);
              const dir = item?.direction_moderate;
              return (
                <div className="a-bar a-bar-plain" key={s.skill_id}>
                  <span className="a-bar-label" title={labels.get(s.skill_id)}>
                    {labels.get(s.skill_id) ?? s.skill_id}
                  </span>
                  <span className="a-bar-track" aria-label={t("level", { level: s.level })}>
                    <span className="a-bar-fill" style={{ width: `${s.level * 20}%` }} />
                  </span>
                  <span
                    className="a-chip"
                    data-tone={dir === "rising" ? "up" : dir === "declining" ? "down" : undefined}
                    title={t("trend")}
                  >
                    {dir === "rising" ? "▲" : dir === "declining" ? "▼" : dir ? "•" : "–"}
                  </span>
                </div>
              );
            })}
          </div>
        </section>
        <aside className="a-span-4 a-stack">
          <div className="a-stats">
            <div className="a-stat">
              <strong>{p.hours_per_week}</strong>
              <span>{t("hours")}</span>
            </div>
            <div className="a-stat">
              <strong>RM {p.budget_myr}</strong>
              <span>{t("budget")}</span>
            </div>
            <div className="a-stat">
              <strong>{p.hrd_eligible ? t("yes") : t("no")}</strong>
              <span>{t("hrd")}</span>
            </div>
          </div>
          {p.interests?.length ? (
            <div className="a-chips">
              {p.interests?.map((i) => (
                <span className="a-chip" key={i}>
                  {i}
                </span>
              ))}
            </div>
          ) : null}
          <div className="a-card" style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span className="a-upload-icon">
              <Building2 size={18} aria-hidden />
            </span>
            {org.ok ? (
              <strong>{org.data.name}</strong>
            ) : (
              <Link className="a-link" href="/app/join">
                {tj("title")}
              </Link>
            )}
          </div>
          <RiseArt className="a-hide-mobile" />
        </aside>
      </div>
    </div>
  );
}
