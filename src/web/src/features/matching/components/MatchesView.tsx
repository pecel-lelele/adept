import Link from "next/link";
import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Badge,
  buttonVariants,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetaBar,
  PageHeader,
  SdgBadge,
  StubBanner,
} from "@/components";
import type { ScenarioId } from "@/lib/api";
import { percent } from "@/lib/utils";

import { fetchMatches } from "../api";

export async function MatchesView({ scenario }: { scenario: ScenarioId }) {
  const t = await getTranslations("matching");
  const result = await fetchMatches(scenario);

  return (
    <section>
      <StubBanner feature="F4 Future-role matching" endpoint="GET /api/v1/matches" />
      <PageHeader title={t("title")} description={t("description")} />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <div className="space-y-3">
          <MetaBar meta={result.data.meta} />
          {result.data.matches.map((m, i) => (
            <Card key={m.role_id}>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle>
                  {i + 1}. {m.label}
                </CardTitle>
                <Badge>{t("score", { score: percent(m.score) })}</Badge>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
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
                <div className="flex gap-2 pt-1">
                  <Link
                    href={`/app/matches/${m.role_id}?scenario=${scenario}`}
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                  >
                    {t("viewDetail")}
                  </Link>
                  <Link
                    href={`/app/pathway?role=${m.role_id}&scenario=${scenario}`}
                    className={buttonVariants({ size: "sm" })}
                  >
                    {t("viewPathway")}
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
