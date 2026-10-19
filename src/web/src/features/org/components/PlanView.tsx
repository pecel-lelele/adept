import { getTranslations } from "next-intl/server";

import { ApiError, MetaBar, PageHeader } from "@/components";
import { PathwaySteps } from "@/features/pathway";
import type { ScenarioId } from "@/lib/api";

import { fetchMembers, fetchPlan } from "../api";

export async function PlanView({ scenario }: { scenario: ScenarioId }) {
  const t = await getTranslations("org");
  const [result, members] = await Promise.all([fetchPlan(scenario), fetchMembers()]);
  const names = Object.fromEntries(
    (members.ok ? members.data.members : []).map((m) => [m.id, m.display_name]),
  );
  return (
    <section>
      <PageHeader title={t("planTitle")} />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <div className="space-y-3">
          <p className="text-sm">
            {t("target", { role: result.data.target_role_id })} ·{" "}
            {t("assigned", { count: result.data.assigned_member_ids.length })}
          </p>
          <MetaBar meta={result.data.meta} />
          <PathwaySteps steps={result.data.steps} memberNames={names} />
        </div>
      )}
    </section>
  );
}
