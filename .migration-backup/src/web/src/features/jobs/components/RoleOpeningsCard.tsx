import { ArrowRight, BriefcaseBusiness } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import { Fold } from "@/components/Fold";
import type { ScenarioId } from "@/lib/api";

import { fetchRoleOpenings } from "../api";
import { OpeningItem, SkillPills, StatusLegend } from "./OpeningItem";

/**
 * Job openings for a role, folded to one line ("12 openings at 5 companies"). Open: how many
 * match the person's skills now and after the plan, the skills employers ask for, and the jobs
 * that match best. `team` hides personal fit (an HR manager has no learner profile here).
 */
export async function RoleOpeningsCard({
  roleId,
  scenario,
  limit = 5,
  variant = "learner",
  open = false,
}: {
  roleId: string;
  scenario: ScenarioId;
  limit?: number;
  variant?: "learner" | "team";
  open?: boolean;
}) {
  const t = await getTranslations("jobs");
  const result = await fetchRoleOpenings(roleId, scenario, limit);
  if (!result.ok) return null;
  const d = result.data;
  const learner = variant === "learner";
  return (
    <Fold
      id="openings"
      open={open}
      icon={<BriefcaseBusiness size={18} aria-hidden />}
      title={t("openings.title")}
      meta={d.open_count ? t("openings.meta", { count: d.open_count, employers: d.employer_count }) : t("openings.metaNone")}
    >
      {!d.open_count ? (
        <p className="a-fold-text">{t("openings.none", { role: d.role_label })}</p>
      ) : (
        <>
          {learner && d.rated > 0 ? (
            <div className="a-bignums" title={t("reach.hint")}>
              <div>
                <strong>{d.ready_now}</strong>
                <span>{t("reach.now")}</span>
              </div>
              <div data-tone="up">
                <strong>{d.ready_after_plan}</strong>
                <span>{t(d.has_plan ? "reach.after" : "reach.noPlan")}</span>
              </div>
            </div>
          ) : null}

          {d.skill_demand.length ? (
            <div className="a-fold-group">
              <h3>{t("openings.asked")}</h3>
              <SkillPills skills={d.skill_demand.map((s) => ({ skill_id: s.skill_id, status: s.status, label: s.label }))} />
              {learner ? <StatusLegend /> : null}
            </div>
          ) : null}

          <ul className="a-jobs">
            {d.openings.map((o) => (
              <OpeningItem key={o.id} o={o} showFit={learner} />
            ))}
          </ul>
          <div className="a-fold-foot">
            <Link className="a-btn is-ghost is-small" href={`/app/jobs?role=${encodeURIComponent(roleId)}&scenario=${scenario}`}>
              {t("openings.all", { count: d.open_count })} <ArrowRight size={14} aria-hidden />
            </Link>
            <MetaBar meta={d.meta} />
          </div>
        </>
      )}
    </Fold>
  );
}
