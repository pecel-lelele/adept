import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EstimateLabel,
  SourceBadge,
  StubBanner,
} from "@/components";
import type { ScenarioId } from "@/lib/api";
import { cn } from "@/lib/utils";

import { fetchOutlook } from "../api";

/** Outlook for one role under each scenario, with low/high range (F3). */
export async function RoleOutlookPanel({
  roleId,
  scenario,
}: {
  roleId: string;
  scenario: ScenarioId;
}) {
  const t = await getTranslations("scenarios");
  const tc = await getTranslations("common.scenario");
  const result = await fetchOutlook(roleId);
  return (
    <Card>
      <CardHeader>
        <StubBanner feature="F3 Scenarios" endpoint="GET /api/v1/scenarios/outlook" />
        <CardTitle>{t("outlook")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {!result.ok ? (
          <ApiError message={result.message} />
        ) : (
          <>
            {result.data.outlooks.map((o) => (
              <div
                key={o.scenario}
                className={cn(
                  "flex justify-between rounded px-2 py-1 text-sm",
                  o.scenario === scenario && "bg-accent",
                )}
              >
                <span>{tc(o.scenario)}</span>
                <span className="tabular-nums">
                  {o.outlook.toFixed(2)} ({t("range", { low: o.low.toFixed(2), high: o.high.toFixed(2) })})
                </span>
              </div>
            ))}
            <div className="flex flex-wrap gap-2">
              <EstimateLabel isEstimate={result.data.meta.is_estimate} />
              <SourceBadge
                sources={result.data.meta.sources}
                snapshotDate={result.data.meta.snapshot_date}
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
