import { getTranslations } from "next-intl/server";

import { ApiError, Card, CardContent, PageHeader, StubBanner } from "@/components";

import { fetchMyOrg } from "../api";

export async function OrgSetupView() {
  const t = await getTranslations("org");
  const result = await fetchMyOrg();
  return (
    <section>
      <StubBanner feature="F7 Organisation mode" endpoint="GET /api/v1/org/me" />
      <PageHeader title={t("setupTitle")} />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <Card>
          <CardContent className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 pt-4 text-sm">
            <span className="text-muted-foreground">Name</span>
            <span>{result.data.name}</span>
            <span className="text-muted-foreground">Type</span>
            <span>{t(`type.${result.data.type}`)}</span>
            <span className="text-muted-foreground">{t("industry")}</span>
            <span>{result.data.industry}</span>
            <span className="text-muted-foreground">{t("size")}</span>
            <span>{result.data.size}</span>
          </CardContent>
        </Card>
      )}
    </section>
  );
}
