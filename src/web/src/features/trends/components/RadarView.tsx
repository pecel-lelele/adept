import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetaBar,
  PageHeader,
  StubBanner,
} from "@/components";
import type { ScenarioId, Schemas } from "@/lib/api";
import { percent } from "@/lib/utils";

import { fetchRadar } from "../api";

const DIRECTIONS = ["rising", "stable", "declining"] as const;

export async function RadarView({
  scenario,
  context = "individual",
}: {
  scenario: ScenarioId;
  context?: "individual" | "organisation";
}) {
  const t = await getTranslations("trends");
  const result = await fetchRadar(scenario);

  return (
    <section>
      <StubBanner feature="F2 AI-trend signal layer" endpoint="GET /api/v1/trends/radar" />
      <PageHeader
        title={context === "organisation" ? t("orgTitle") : t("title")}
        description={t("description")}
      />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <div className="space-y-4">
          <MetaBar meta={result.data.meta} />
          <div className="grid gap-4 md:grid-cols-3">
            {DIRECTIONS.map((direction) => (
              <Card key={direction}>
                <CardHeader>
                  <CardTitle>{t(`direction.${direction}`)}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {result.data.items
                    .filter((item) => item.direction === direction)
                    .map((item) => (
                      <SignalRow key={`${item.entity_type}-${item.entity_id}`} item={item} />
                    ))}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

async function SignalRow({ item }: { item: Schemas["TrendSignal"] }) {
  const t = await getTranslations("trends");
  const growth = `${item.growth_rate > 0 ? "+" : ""}${percent(item.growth_rate)}`;
  return (
    <div className="text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">{item.label}</span>
        <Badge variant="outline">{t(`entity.${item.entity_type}`)}</Badge>
      </div>
      <div className="text-xs text-muted-foreground">
        {t("growth")} {growth} · {t("aiExposure")} {percent(item.ai_exposure)} · {t("automation")}{" "}
        {percent(item.automation_share)} / {t("augmentation")} {percent(item.augmentation_share)}
      </div>
    </div>
  );
}
