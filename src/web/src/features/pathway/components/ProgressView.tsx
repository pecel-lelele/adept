import { getTranslations } from "next-intl/server";

import { ApiError, Card, CardContent, PageHeader, StubBanner } from "@/components";
import type { ScenarioId } from "@/lib/api";

import { fetchPathway } from "../api";

export async function ProgressView({ roleId, scenario }: { roleId: string; scenario: ScenarioId }) {
  const t = await getTranslations("pathway");
  const result = await fetchPathway(roleId, scenario);
  return (
    <section>
      <StubBanner feature="F5 Progress & badges" endpoint="GET /api/v1/pathway" />
      <PageHeader title={t("progressTitle")} description={t("progressBody")} />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <Card>
          <CardContent className="space-y-2 pt-4 text-sm">
            {result.data.steps.map((s) => (
              <label key={s.order} className="flex items-center gap-2">
                <input type="checkbox" disabled /> {s.order}. {s.skill_id}
              </label>
            ))}
          </CardContent>
        </Card>
      )}
    </section>
  );
}
