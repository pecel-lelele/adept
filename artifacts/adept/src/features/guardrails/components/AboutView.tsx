import { Check, ShieldCheck, X } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { ApiError, Badge } from "@/components";
import { SiteFooter, SiteHeader } from "@/components/shell/Site";
import { call, getApi } from "@/lib/api";

/** About page (F8, owner M3): LLM disclosure, methodology, guardrails, sources, fairness. */
export async function AboutView() {
  const t = await getTranslations("guardrails");
  const tl = await getTranslations("ui.landing");
  const api = await getApi();
  const [disclosure, sources, fairness] = await Promise.all([
    call(api.GET("/api/v1/guardrails/disclosure")),
    call(api.GET("/api/v1/guardrails/sources")),
    call(api.GET("/api/v1/guardrails/fairness")),
  ]);

  return (
    <div className="a-page">
      <SiteHeader />
      <main id="a-main" className="a-wrap a-about">
        <span className="a-eyebrow is-square">{tl("navAbout")}</span>
        <h1 className="a-display">{t("title")}</h1>
        <p className="a-hero2-lead">{t("methodBody")}</p>

        <div className="a-about-grid">
          <section className="a-card">
            <h2>{t("llmTitle")}</h2>
            {!disclosure.ok ? (
              <ApiError message={disclosure.message} />
            ) : (
              <>
                <p>
                  {disclosure.data.llm_enabled
                    ? t("llmProvider", { provider: disclosure.data.provider, model: disclosure.data.model })
                    : t("llmNone")}
                </p>
                {disclosure.data.llm_enabled
                  ? disclosure.data.purpose.map((p) => (
                      <p key={p} className="a-muted">
                        {p}
                      </p>
                    ))
                  : null}
                <span className="a-chip">
                  {t("llmCalls", { calls: disclosure.data.calls_logged, rejected: disclosure.data.rejected_ids })}
                </span>
              </>
            )}
          </section>

          {disclosure.ok ? (
            <section className="a-card is-sage">
              <h2>{t("rulesTitle")}</h2>
              <ul className="a-checklist" style={{ margin: 0 }}>
                {disclosure.data.rules.map((rule) => (
                  <li key={rule}>
                    <ShieldCheck size={15} aria-hidden /> {rule}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="a-card is-wide">
            <h2>{t("sourcesTitle")}</h2>
            {!sources.ok ? (
              <ApiError message={sources.message} />
            ) : (
              <div className="a-source-rows">
                {sources.data.sources.map((s) => (
                  <div key={`${s.name}-${s.used_for}`}>
                    {s.url ? (
                      <a href={s.url} className="a-link" target="_blank" rel="noreferrer">
                        {s.name}
                      </a>
                    ) : (
                      <strong style={{ fontWeight: 500 }}>{s.name}</strong>
                    )}
                    <Badge variant={s.kind === "mock" ? "warning" : "outline"}>{t(`sourceKind.${s.kind}`)}</Badge>
                    <small>
                      {s.used_for} · {t("records", { count: s.records })} · {s.retrieved_at}
                      {s.last_synced_at
                        ? ` · ${t("lastSynced", { date: s.last_synced_at.slice(0, 16).replace("T", " ") })}`
                        : null}
                    </small>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="a-card">
            <h2>{t("fairnessTitle")}</h2>
            {!fairness.ok ? (
              <ApiError message={fairness.message} />
            ) : (
              <>
                <Badge variant={fairness.data.passed ? "success" : "danger"}>
                  {fairness.data.passed ? t("fairnessPassed") : t("fairnessFailed")}
                </Badge>
                <ul className="a-checklist">
                  {fairness.data.counterfactual_checks.map((c) => (
                    <li key={c.name}>
                      {c.passed ? <Check size={15} aria-hidden /> : <X size={15} aria-hidden />}
                      <span>
                        {c.name}. <span className="a-muted">{c.detail}</span>
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="a-small a-muted">
                  {t("protectedTitle")}: {fairness.data.protected_attributes.join(", ")}
                </p>
              </>
            )}
          </section>

          <section className="a-card">
            <h2>{t("limitsTitle")}</h2>
            <p>{t("limitsBody")}</p>
          </section>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
