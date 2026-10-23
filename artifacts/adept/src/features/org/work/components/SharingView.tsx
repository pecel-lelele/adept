import { Eye, EyeOff } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ApiError, PageHeader } from "@/components";
import { ActionForm } from "@/features/pathway/components/ActionForm";
import { fetchMyProfile, fetchSkillCatalogue } from "@/features/profile/api";
import type { WorkspaceOption } from "@/lib/auth/workspaces";

import { setSharingAction } from "../actions";

/**
 * What this organisation can see. Members choose whether managers may use their skill levels
 * for team gaps and programme matching; personal plans, matches and Adi chats are never shared.
 */
export async function SharingView({ org }: { org: WorkspaceOption }) {
  const t = await getTranslations("org.work");
  const [profile, catalogue] = await Promise.all([fetchMyProfile(), fetchSkillCatalogue()]);
  if (!profile.ok) return <ApiError message={profile.message} />;
  if (!catalogue.ok) return <ApiError message={catalogue.message} />;
  const labels = new Map(catalogue.ok ? catalogue.data.skills.map((s) => [s.id, s.label]) : []);
  const skills = profile.ok ? [...profile.data.skills].sort((a, b) => b.level - a.level) : [];
  const shared = org.skills_shared;
  return (
    <div className="a-view">
      <PageHeader eyebrow={org.name} title={t("sharingTitle")} description={t("sharingDesc", { org: org.name })} />
      <div className="a-split is-wide">
        <section className="a-card">
          <div className="a-card-head">
            <h2>{shared ? t("sharingOnTitle", { org: org.name }) : t("sharingOffTitle", { org: org.name })}</h2>
          </div>
          <p className="a-small">{shared ? t("sharingOnBody") : t("sharingOffBody")}</p>
          <ActionForm
            action={setSharingAction}
            fields={{ share: shared ? "off" : "on", org_id: org.id }}
            label={shared ? t("stopSharing") : t("shareNow", { org: org.name })}
            variant={shared ? "outline" : "default"}
          />
          <h3 className="a-small a-muted" style={{ marginTop: 20 }}>
            {t("levelsTitle")}
          </h3>
          {skills.length ? (
            <ul className="a-rows">
              {skills.map((s) => (
                <li key={s.skill_id}>
                  <strong>{labels.get(s.skill_id) ?? s.skill_id}</strong>
                  <span className="a-muted a-small">{t("level", { level: s.level })}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="a-muted a-small">
              {t("noSkills")} <Link href="/app/onboarding">{t("addSkills")}</Link>
            </p>
          )}
        </section>
        <aside className="a-stack">
          <div className="a-card is-sage">
            <div className="a-card-head">
              <h2>
                <Eye size={16} aria-hidden /> {t("seesTitle", { org: org.name })}
              </h2>
            </div>
            <ul className="a-ticklist">
              <li>{t("sees1")}</li>
              <li>{t("sees2")}</li>
              <li>{shared ? t("sees3On") : t("sees3Off")}</li>
            </ul>
          </div>
          <div className="a-card">
            <div className="a-card-head">
              <h2>
                <EyeOff size={16} aria-hidden /> {t("neverTitle")}
              </h2>
            </div>
            <ul className="a-ticklist">
              <li>{t("never1")}</li>
              <li>{t("never2")}</li>
              <li>{t("never3")}</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
