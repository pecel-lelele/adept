import { ArrowRight, Building2, CalendarClock, ClipboardCheck, EyeOff, Share2 } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ErrorState, Kpis, PageHeader } from "@/components";
import type { WorkspaceOption } from "@/lib/auth/workspaces";

import { byStatus, fetchMyProgrammes } from "../api";

/** Organisation home for a member: their own agreements, programmes and sharing choice. */
export async function WorkHomeView({ org }: { org: WorkspaceOption }) {
  const t = await getTranslations("org.work");
  const result = await fetchMyProgrammes();
  if (!result.ok) return <ErrorState failure={result} />;
  const { pending, accepted } = byStatus(result.data.assignments);
  return (
    <div className="a-view">
      <PageHeader eyebrow={org.name} title={t("homeTitle", { org: org.name })} description={t("homeDesc")}>
        <span className="a-work-context">
          <Building2 size={13} aria-hidden /> {t("memberOf", { org: org.name })}
        </span>
      </PageHeader>

      <Kpis
        items={[
          { label: t("kPending"), value: pending.length, icon: <ClipboardCheck size={15} />, tone: pending.length ? "warn" : undefined, note: t("kPendingNote") },
          { label: t("kActive"), value: accepted.length, icon: <CalendarClock size={15} />, note: t("kActiveNote") },
          {
            label: t("kSharing"),
            value: org.skills_shared ? t("sharingOn") : t("sharingOff"),
            icon: <Share2 size={15} />,
            tone: org.skills_shared ? "up" : undefined,
            note: t("kSharingNote"),
          },
        ]}
      />

      {pending.length ? (
        <section className="a-card is-accent">
          <div className="a-card-head">
            <h2>{t("waitingTitle")}</h2>
          </div>
          <ul className="a-rows">
            {pending.map((a) => (
              <li key={a.agreement.programme_id}>
                <strong>{a.agreement.title}</strong>
                <span className="a-muted a-small">
                  {a.agreement.role_label} · {t("due", { date: a.agreement.target_date })}
                  {a.agreement.mandatory ? ` · ${t("required")}` : ""}
                </span>
              </li>
            ))}
          </ul>
          <Link className="a-btn" href="/work/plan">
            {t("reviewAgreement")} <ArrowRight size={14} aria-hidden />
          </Link>
        </section>
      ) : null}

      <div className="a-split">
        <section className="a-card">
          <div className="a-card-head">
            <h2>{t("activeTitle")}</h2>
          </div>
          {accepted.length ? (
            <ul className="a-rows">
              {accepted.map((a) => (
                <li key={a.agreement.programme_id}>
                  <Link href={`/work/progress?role=${encodeURIComponent(a.agreement.role_id)}`}>
                    <strong>{a.agreement.title}</strong>
                  </Link>
                  <span className="a-muted a-small">
                    {t("activeLine", {
                      role: a.agreement.role_label,
                      date: a.agreement.target_date,
                      hours: a.agreement.hours_per_week,
                      budget: Math.round(a.agreement.budget_myr),
                    })}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="a-muted a-small">{t("noActive", { org: org.name })}</p>
          )}
        </section>
        <aside className="a-card is-sage">
          <div className="a-card-head">
            <h2>
              <EyeOff size={16} aria-hidden /> {t("privacyTitle")}
            </h2>
          </div>
          <p className="a-small">{t("privacySees", { org: org.name })}</p>
          <p className="a-small">{t("privacyNever")}</p>
          <Link className="a-link" href="/work/skills">
            {org.skills_shared ? t("manageSharing") : t("startSharing")}
          </Link>
        </aside>
      </div>
    </div>
  );
}
