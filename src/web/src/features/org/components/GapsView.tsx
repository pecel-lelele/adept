import { getTranslations } from "next-intl/server";

import { ApiError, MetaBar, PageHeader, StubBanner } from "@/components";
import type { ScenarioId } from "@/lib/api";
import { percent } from "@/lib/utils";

import { fetchGaps } from "../api";

/** Team skills-gap heatmap: rows = target roles, columns = skills. */
export async function GapsView({ scenario }: { scenario: ScenarioId }) {
  const t = await getTranslations("org");
  const result = await fetchGaps(scenario);
  return (
    <section>
      <StubBanner feature="F7 Organisation mode" endpoint="GET /api/v1/org/gaps" />
      <PageHeader title={t("gapsTitle")} description={t("gapLegend")} />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <div className="space-y-3">
          <MetaBar meta={result.data.meta} />
          <div className="overflow-x-auto">
            <table className="text-sm">
              <thead>
                <tr>
                  <th />
                  {result.data.skills.map((s) => (
                    <th key={s.id} className="px-2 py-1 text-left font-medium">
                      {s.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.data.role_ids.map((roleId) => (
                  <tr key={roleId}>
                    <th className="px-2 py-1 text-left font-medium">{roleId}</th>
                    {result.data.skills.map((s) => {
                      const gap =
                        result.data.cells.find((c) => c.role_id === roleId && c.skill_id === s.id)
                          ?.gap ?? 0;
                      return (
                        <td
                          key={s.id}
                          className="px-2 py-1 text-center tabular-nums"
                          style={{ backgroundColor: `rgba(220, 38, 38, ${gap * 0.8})` }}
                        >
                          {percent(gap)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
