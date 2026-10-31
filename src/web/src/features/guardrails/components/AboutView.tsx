import { ArrowUpRight, Check, ShieldCheck, X } from "lucide-react";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { Suspense } from "react";

import { Badge, ErrorState } from "@/components";
import { SiteFooter, SiteHeader } from "@/components/shell/Site";
import { call, getApi } from "@/lib/api";

import styles from "./about.module.css";

async function EvidenceRegister() {
  const t = await getTranslations("guardrails");
  const api = await getApi();
  const [disclosure, sources, fairness] = await Promise.all([
    call(api.GET("/api/v1/guardrails/disclosure")),
    call(api.GET("/api/v1/guardrails/sources")),
    call(api.GET("/api/v1/guardrails/fairness")),
  ]);

  return (
    <div className={styles.sections}>
      <section className={styles.panel} id="ai-use" aria-labelledby="ai-use-title">
        <div className={styles.panelHeading}>
          <h2 id="ai-use-title">{t("llmTitle")}</h2>
          {disclosure.ok ? <span className={styles.status}>{disclosure.data.llm_enabled ? t("llmProvider", { provider: disclosure.data.provider, model: disclosure.data.model }) : t("llmNone")}</span> : null}
        </div>
        {!disclosure.ok ? <ErrorState failure={disclosure} /> : (
          <>
            <p className={styles.lead}>{t("llmSummary")}</p>
            {disclosure.data.llm_enabled && disclosure.data.purpose.length ? (
              <ul className={styles.compactList}>{disclosure.data.purpose.map((purpose) => <li key={purpose}>{purpose}</li>)}</ul>
            ) : null}
            <div className={styles.methodStrip}>
              <strong>{t("rulesTitle")}</strong>
              <ul>{disclosure.data.rules.map((rule) => <li key={rule}><ShieldCheck size={16} aria-hidden />{rule}</li>)}</ul>
            </div>
            <details className={styles.disclosure}>
              <summary>{t("registryTitle")}</summary>
              <ul className={styles.rows}>
                {disclosure.data.registry.map((entry) => (
                  <li key={entry.id}>
                    <a href={entry.url} target="_blank" rel="noreferrer">{entry.name}<ArrowUpRight size={14} aria-hidden /></a>
                    <span>{t(`registryPurpose.${entry.id}`)}</span>
                  </li>
                ))}
              </ul>
            </details>
            <p className={styles.tiny}>{t("llmCalls", { calls: disclosure.data.calls_logged, rejected: disclosure.data.rejected_ids })}</p>
          </>
        )}
      </section>

      <section className={styles.panel} id="data-sources" aria-labelledby="data-sources-title">
        <div className={styles.panelHeading}><h2 id="data-sources-title">{t("sourcesTitle")}</h2></div>
        {!sources.ok ? <ErrorState failure={sources} /> : (
          <div className={styles.sourceGroups}>
            {(["live_api", "verified_page", "curated", "synthetic", "mock"] as const).map((kind) => {
              const group = sources.data.sources.filter((source) => source.kind === kind);
              return group.length ? (
                <details key={kind} className={styles.disclosure}>
                  <summary>{t(`sourceKind.${kind}`)} <span>({group.length})</span></summary>
                  <ul className={styles.rows}>
                    {group.map((source) => (
                      <li key={`${source.name}-${source.used_for}`}>
                        <div className={styles.sourceName}>
                          {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.name}<ArrowUpRight size={14} aria-hidden /></a> : <strong>{source.name}</strong>}
                        </div>
                        <span>{source.used_for}</span>
                        <small>{t("records", { count: source.records })} · {source.retrieved_at}{source.last_synced_at ? ` · ${t("lastSynced", { date: source.last_synced_at.slice(0, 16).replace("T", " ") })}` : ""}</small>
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null;
            })}
          </div>
        )}
      </section>

      <div className={styles.endGrid}>
        <section className={styles.panel} id="checks" aria-labelledby="checks-title">
          <h2 id="checks-title">{t("fairnessTitle")}</h2>
          {!fairness.ok ? <ErrorState failure={fairness} /> : (
            <>
              <Badge variant={fairness.data.passed ? "success" : "danger"}>{fairness.data.passed ? t("fairnessPassed") : t("fairnessFailed")}</Badge>
              <ul className={styles.checks}>{fairness.data.counterfactual_checks.map((check) => (
                <li key={check.name}>{check.passed ? <Check size={16} aria-hidden /> : <X size={16} aria-hidden />}<span><strong>{check.name}</strong><small>{check.detail}</small></span></li>
              ))}</ul>
              <p className={styles.tiny}>{t("protectedTitle")}: {fairness.data.protected_attributes.join(", ")}</p>
            </>
          )}
        </section>
        <section className={`${styles.panel} ${styles.limits}`} aria-labelledby="limits-title">
          <h2 id="limits-title">{t("limitsTitle")}</h2>
          <p>{t("limitsBody")}</p>
        </section>
      </div>
    </div>
  );
}

/** Public data and AI register. API evidence streams after the page frame. */
export async function AboutView() {
  const t = await getTranslations("guardrails");
  const tl = await getTranslations("ui.landing");
  const ti = await getTranslations("impact");
  return (
    <div className="a-page">
      <SiteHeader />
      <main id="a-main" className={`a-wrap ${styles.page}`}>
        <div className={styles.intro}>
          <div>
            <h1 className="a-display">{tl("navAbout")}</h1>
            <p>{t("methodBody")}</p>
          </div>
          <Link className={styles.impactLink} href="/impact">{ti("aboutLink")}<ArrowUpRight size={17} aria-hidden /></Link>
        </div>
        <nav className={styles.index} aria-label={t("title")}>
          <a href="#ai-use">{t("llmTitle")}</a>
          <a href="#data-sources">{t("sourcesTitle")}</a>
          <a href="#checks">{t("fairnessTitle")}</a>
        </nav>
        <Suspense fallback={<div className={styles.loading} role="status" aria-live="polite"><span className="a-sr">{t("sourcesTitle")}</span><i /><i /><i /></div>}>
          <EvidenceRegister />
        </Suspense>
      </main>
      <SiteFooter />
    </div>
  );
}
