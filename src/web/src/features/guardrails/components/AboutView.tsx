import Link from "next/link";
import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageHeader,
} from "@/components";
import { call, getApi } from "@/lib/api";

/** About page (F8, owner M3): LLM disclosure, methodology, guardrails, sources, fairness. */
export async function AboutView() {
  const t = await getTranslations("guardrails");
  const api = await getApi();
  const [disclosure, sources, fairness] = await Promise.all([
    call(api.GET("/api/v1/guardrails/disclosure")),
    call(api.GET("/api/v1/guardrails/sources")),
    call(api.GET("/api/v1/guardrails/fairness")),
  ]);

  return (
    <main className="mx-auto max-w-3xl space-y-4 px-4 py-10">
      <PageHeader title={t("title")} />
      <Card>
        <CardHeader>
          <CardTitle>{t("llmTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {!disclosure.ok ? (
            <ApiError message={disclosure.message} />
          ) : (
            <>
              <p>
                {disclosure.data.llm_enabled
                  ? t("llmProvider", {
                      provider: disclosure.data.provider,
                      model: disclosure.data.model,
                    })
                  : t("llmNone")}
              </p>
              {disclosure.data.llm_enabled
                ? disclosure.data.purpose.map((p) => (
                    <p key={p} className="text-muted-foreground">
                      {p}
                    </p>
                  ))
                : null}
              <p className="text-xs text-muted-foreground">
                {t("llmCalls", {
                  calls: disclosure.data.calls_logged,
                  rejected: disclosure.data.rejected_ids,
                })}
              </p>
            </>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{t("methodTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">{t("methodBody")}</CardContent>
      </Card>
      {disclosure.ok ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("rulesTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {disclosure.data.rules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle>{t("sourcesTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {!sources.ok ? (
            <ApiError message={sources.message} />
          ) : (
            sources.data.sources.map((s) => (
              <div key={`${s.name}-${s.used_for}`} className="flex flex-wrap items-baseline gap-2">
                {s.url ? (
                  <a href={s.url} className="font-medium underline" target="_blank" rel="noreferrer">
                    {s.name}
                  </a>
                ) : (
                  <span className="font-medium">{s.name}</span>
                )}
                <Badge variant={s.kind === "mock" ? "warning" : "outline"}>
                  {t(`sourceKind.${s.kind}`)}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {s.used_for} · {t("records", { count: s.records })} · {s.retrieved_at}
                  {s.last_synced_at
                    ? ` · ${t("lastSynced", { date: s.last_synced_at.slice(0, 16).replace("T", " ") })}`
                    : null}
                </span>
              </div>
            ))
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{t("fairnessTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {!fairness.ok ? (
            <ApiError message={fairness.message} />
          ) : (
            <>
              <Badge variant={fairness.data.passed ? "success" : "danger"}>
                {fairness.data.passed ? t("fairnessPassed") : t("fairnessFailed")}
              </Badge>
              {fairness.data.counterfactual_checks.map((c) => (
                <p key={c.name}>
                  {c.passed ? "✓" : "✗"} {c.name}.{" "}
                  <span className="text-muted-foreground">{c.detail}</span>
                </p>
              ))}
              <p className="text-xs text-muted-foreground">
                {t("protectedTitle")}: {fairness.data.protected_attributes.join(", ")}
              </p>
            </>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{t("limitsTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">{t("limitsBody")}</CardContent>
      </Card>
      <Link href="/" className="text-sm underline">
        ←
      </Link>
    </main>
  );
}
