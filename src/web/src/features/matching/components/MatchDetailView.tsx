import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetaBar,
  PageHeader,
  ScoreBreakdown,
  SdgBadge,
  StubBanner,
} from "@/components";
import type { ScenarioId } from "@/lib/api";

import { fetchMatch } from "../api";
import { componentLabels } from "./labels";

export async function MatchDetailView({ roleId, scenario }: { roleId: string; scenario: ScenarioId }) {
  const t = await getTranslations("matching");
  const result = await fetchMatch(roleId, scenario);
  if (!result.ok) return <ApiError message={result.message} />;
  const m = result.data;

  return (
    <section className="space-y-4">
      <StubBanner feature="F4 Future-role matching" endpoint="GET /api/v1/matches/{role_id}" />
      <PageHeader title={m.label}>
        <MetaBar meta={m.meta} />
      </PageHeader>
      <Card>
        <CardHeader>
          <CardTitle>{t("breakdown")}</CardTitle>
        </CardHeader>
        <CardContent>
          <ScoreBreakdown score={m.score} components={m.components} labels={await componentLabels()} />
        </CardContent>
      </Card>
      <Card>
        <CardContent className="space-y-2 pt-4 text-sm">
          <div className="flex flex-wrap gap-1">
            {m.sdg_targets.map((s) => (
              <SdgBadge key={s.target} target={s} />
            ))}
          </div>
          <p>
            <span className="text-muted-foreground">{t("missing")}:</span>{" "}
            {m.missing_skills.map((s) => s.label).join(", ") || "—"}
          </p>
          <p>
            <span className="text-muted-foreground">{t("partial")}:</span>{" "}
            {m.partial_skills.map((s) => s.label).join(", ") || "—"}
          </p>
        </CardContent>
      </Card>
    </section>
  );
}
