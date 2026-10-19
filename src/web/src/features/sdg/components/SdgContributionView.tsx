import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetaBar,
  PageHeader,
  SdgBadge,
  StubBanner,
} from "@/components";

import { fetchMyContribution } from "../api";

export async function SdgContributionView({
  context = "individual",
}: {
  context?: "individual" | "organisation";
}) {
  const t = await getTranslations("sdg");
  const result = await fetchMyContribution();
  return (
    <section>
      <StubBanner feature="F6 SDG mapping" endpoint="GET /api/v1/sdg/contribution/me" />
      <PageHeader title={context === "organisation" ? t("orgTitle") : t("title")} />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <div className="space-y-4">
          <MetaBar meta={result.data.meta} />
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>{t("goals")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                {result.data.goals_summary.map((g) => (
                  <div key={g.goal} className="flex justify-between">
                    <span>
                      SDG {g.goal} · {g.label}
                    </span>
                    <span className="text-muted-foreground">
                      {t("linkCount", { count: g.link_count })}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>{t("links")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {result.data.links.map((link, i) => (
                  <div key={`${link.target.target}-${i}`} className="flex items-start gap-2">
                    <SdgBadge target={link.target} />
                    <span>{link.reason}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </section>
  );
}
