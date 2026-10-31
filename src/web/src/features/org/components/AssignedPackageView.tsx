import { getTranslations } from "next-intl/server";

import { ActionForm } from "@/features/pathway/components/ActionForm";
import { call, getApi } from "@/lib/api";

import { acceptPackageAction } from "../funding-actions";
import { proposePackageRoleAction } from "../work/actions";
import { RoleProposalForm } from "../work/components/RoleProposalForm";
import { PathwaySteps } from "@/features/pathway/components/PathwaySteps";
import { PlanTotals } from "@/features/pathway/components/PlanTotals";

/**
 * A team plan HR assigned with a quick package (organisation workspace). Accepting turns it into
 * a work programme; it never replaces the member's personal plan. Hidden once accepted.
 */
export async function AssignedPackageView({ acceptedIds = [], orgId, roles = {} }: { acceptedIds?: string[]; orgId?: string; roles?: Record<string, string> }) {
  const api = await getApi();
  const result = await call(api.GET("/api/v1/org/packages/assigned"));
  if (!result.ok || !result.data) return null;
  const p = result.data;
  if (acceptedIds.includes(`pkg-${p.token.slice(0, 12)}`)) return null;
  const t = await getTranslations("org.packages");
  return (
    <section className="a-card">
      <h2>
        {t("assigned")}: {p.pathway.role_label}
      </h2>
      <p>
        {t(`kind.${p.kind}`)} · RM {p.pathway.total_cost_myr} · {t("weeks", { count: p.pathway.total_weeks })}
      </p>
      <p>{t("acceptHint")}</p>
      <details className="a-disclosure">
        <summary>{t("preview")}</summary>
        <PathwaySteps steps={p.pathway.steps} />
        <PlanTotals plan={p.pathway} />
        <p>
          {t("unmet")}: {(p.pathway.unmet ?? []).map((u) => u.label).join(", ") || "—"}
        </p>
      </details>
      <ActionForm action={acceptPackageAction} label={t("accept")} fields={{ token: p.token, ...(orgId ? { org_id: orgId } : {}) }} />
      <RoleProposalForm action={proposePackageRoleAction} fields={{ token: p.token, ...(orgId ? { org_id: orgId } : {}) }} roleId={p.pathway.role_id} roles={roles} />
    </section>
  );
}
