import { getTranslations } from "next-intl/server";

import { ApiError, MetaBar, PageHeader, StubBanner } from "@/components";
import type { ScenarioId } from "@/lib/api";

import { fetchPathway } from "../api";
import { PathwaySteps } from "./PathwaySteps";

export async function PathwayView({ roleId, scenario }: { roleId: string; scenario: ScenarioId }) {
  const t = await getTranslations("pathway");
  const result = await fetchPathway(roleId, scenario);
  return (
    <section>
      <StubBanner feature="F5 Reskilling pathway" endpoint="GET /api/v1/pathway" />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <>
          <PageHeader
            title={t("title")}
            description={`${result.data.role_id} · ${t("totalWeeks", { weeks: result.data.total_weeks })}`}
          >
            <MetaBar meta={result.data.meta} />
          </PageHeader>
          <PathwaySteps steps={result.data.steps} />
        </>
      )}
    </section>
  );
}
