import { getTranslations } from "next-intl/server";

import { ApiError, MetaBar, PageHeader, StubBanner } from "@/components";
import { PathwaySteps } from "@/features/pathway";

import { fetchPlan } from "../api";

export async function PlanView() {
  const t = await getTranslations("org");
  const result = await fetchPlan();
  return (
    <section>
      <StubBanner feature="F7 Organisation mode" endpoint="GET /api/v1/org/plan" />
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
          <PathwaySteps steps={result.data.steps} />
        </div>
      )}
    </section>
  );
}
