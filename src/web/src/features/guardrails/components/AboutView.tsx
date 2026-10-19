import Link from "next/link";
import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageHeader,
  SourceBadge,
  StubBanner,
} from "@/components";
import { call, getApi } from "@/lib/api";

/** About page (F8, owner M3): LLM disclosure, methodology, data sources, limitations. */
export async function AboutView() {
  const t = await getTranslations("guardrails");
  const api = await getApi();
  const freshness = await call(api.GET("/api/v1/meta/data-freshness"));

  const sections = [
    { title: t("llmTitle"), body: t("llmNone") },
    { title: t("methodTitle"), body: t("methodBody") },
    { title: t("limitsTitle"), body: t("limitsBody") },
  ];

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <StubBanner feature="F8 Guardrails & transparency" endpoint="GET /api/v1/meta/data-freshness" />
      <PageHeader title={t("title")} />
      <div className="space-y-4">
        {sections.map((s) => (
          <Card key={s.title}>
            <CardHeader>
              <CardTitle>{s.title}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm">{s.body}</CardContent>
          </Card>
        ))}
        <Card>
          <CardHeader>
            <CardTitle>{t("sourcesTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            {freshness.ok ? (
              <SourceBadge
                sources={freshness.data.sources}
                snapshotDate={freshness.data.snapshot_date}
              />
            ) : (
              <ApiError message={freshness.message} />
            )}
          </CardContent>
        </Card>
        <Link href="/" className="text-sm underline">
          ←
        </Link>
      </div>
    </main>
  );
}
