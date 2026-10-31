import { ArrowUpRight } from "lucide-react";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { Suspense } from "react";

import { ErrorState } from "@/components";
import { SiteFooter, SiteHeader } from "@/components/shell/Site";

import { fetchImpact } from "../api";
import type { EvidenceItem, ImpactSummary } from "../types";
import styles from "./impact.module.css";

type Translate = Awaited<ReturnType<typeof getTranslations<"impact">>>;

const pct = (share: number) => `${Math.round(share * 100)}%`;
const num = (value: number) => String(Math.round(value * 10) / 10);

const FEATURES = ["matching", "radar", "profile", "pathway", "scenarios", "org", "catalogue"] as const;
const PROVIDERS = ["mooc", "university", "industry_body", "professional_body", "private_provider", "government"] as const;
type Feature = (typeof FEATURES)[number];
const isFeature = (key: string): key is Feature => (FEATURES as readonly string[]).includes(key);

function Metric({ label, value, note, formula }: { label: string; value: string; note: string; formula: string }) {
  return (
    <article className={styles.metric}>
      <h3>{label}</h3>
      <strong className={styles.value}>{value}</strong>
      <p>{note}</p>
      <p className={styles.metricMethod}>{formula}</p>
    </article>
  );
}

function Evidence({ item, t }: { item: EvidenceItem; t: Translate }) {
  return (
    <li className={styles.evidenceItem}>
      <div className={styles.evidenceFigure}><small>{item.scope}</small><strong>{item.figure}</strong></div>
      <div className={styles.evidenceContent}>
        <h3>{item.claim}</h3>
        <a href={item.url} target="_blank" rel="noreferrer">{item.publisher}<ArrowUpRight size={14} aria-hidden /></a>
        <details className={styles.quoteDetail}>
          <summary>{t("why.lead")}</summary>
          {isFeature(item.feature) ? <p>{t(`feature.${item.feature}`)}</p> : null}
          <blockquote>“{item.quote}”</blockquote>
          <small>{t("retrieved", { date: item.retrieved_at })}{item.published_at ? ` · ${t("published", { date: item.published_at })}` : ""}</small>
        </details>
      </div>
    </li>
  );
}

function Body({ d, t, providers }: { d: ImpactSummary; t: Translate; providers: Record<string, string> }) {
  const moderate = d.aggregates.find((a) => a.scenario === "moderate");
  const fast = d.aggregates.find((a) => a.scenario === "fast");
  if (!moderate || !fast) return null;
  const c = d.catalogue;
  return (
    <>
      <p className={styles.context}>
        {d.meta.observed_to && Date.parse(d.meta.snapshot_date) - Date.parse(d.meta.observed_to) > 60 * 864e5
          ? t("basisArchived", { count: d.personas.length })
          : t("basis", { count: d.personas.length })}
      </p>

      <section className={styles.section} aria-labelledby="impact-results">
        <div className={styles.sectionHeading}><h2 id="impact-results">{t("personas.title")}</h2></div>
        <div className={styles.metrics}>
          <Metric label={t("free.label")} value={pct(moderate.median_free_course_share)} note={t("free.note", { hours: pct(moderate.median_free_hours_share), hrd: pct(moderate.median_hrd_course_share) })} formula={t("free.formula")} />
          <Metric label={t("hours.label")} value={num(moderate.median_total_hours)} note={t("hours.note", { fast: num(fast.median_total_hours) })} formula={t("hours.formula")} />
          <Metric label={t("sdg.label")} value={num(moderate.median_sdg_target_count)} note={t("sdg.note")} formula={t("sdg.formula")} />
          <Metric label={t("scenario.label")} value={num(moderate.median_top5_changed)} note={t("scenario.note", { count: d.personas.filter((p) => p.top_role_changed).length })} formula={t("scenario.formula")} />
        </div>
        <details className={styles.details}>
          <summary>{t("personas.title")}</summary>
          <div className={styles.scroll}>
            <table className={styles.table}>
              <thead><tr><th scope="col">{t("personas.persona")}</th><th scope="col">{t("personas.role")}</th><th scope="col">{t("personas.hours")}</th><th scope="col">{t("personas.free")}</th><th scope="col">{t("personas.hrd")}</th><th scope="col">{t("personas.sdg")}</th><th scope="col">{t("personas.changed")}</th></tr></thead>
              <tbody>{d.personas.map((p) => <tr key={p.persona_id}><th scope="row">{p.persona_id}</th><td>{p.moderate.top_role_label}</td><td>{num(p.moderate.total_hours)}</td><td>{pct(p.moderate.free_course_share)}</td><td>{pct(p.moderate.hrd_course_share)}</td><td>{p.moderate.sdg_target_count}</td><td>{p.top5_changed}</td></tr>)}</tbody>
            </table>
          </div>
          <p className={styles.small}>{t("personas.note")}</p>
        </details>
      </section>

      <section className={styles.section} aria-labelledby="impact-coverage">
        <div className={styles.sectionHeading}><h2 id="impact-coverage">{t("coverage.title")}</h2></div>
        <div className={styles.metrics}>
          <Metric label={t("coverage.label")} value={String(c.course_count)} note={t("coverage.note", { roles: c.role_count, skills: c.skill_count, fresh: pct(c.verified_recent_share), days: c.verified_window_days, date: c.as_of })} formula={t("coverage.formula")} />
          <Metric label={t("catalogueFree.label")} value={pct(c.free_course_share)} note={t("catalogueFree.note", { count: c.free_course_count, hours: num(c.free_hours) })} formula={t("catalogueFree.formula")} />
          <Metric label={t("catalogueSdg.label")} value={String(c.sdg_target_count)} note={t("catalogueSdg.note", { links: c.role_sdg_link_count, targets: c.target_role_count })} formula={t("catalogueSdg.formula")} />
          <Metric label={t("fairness.label")} value={String(d.fairness.max_rank_change)} note={t("fairness.note", { variants: d.fairness.variants_tested, passed: String(d.fairness.guardrail_report_passed) })} formula={t("fairness.formula")} />
        </div>
        <details className={styles.details}>
          <summary>{t("coverage.title")}: {t("coverage.language")} / {t("coverage.provider")}</summary>
          <dl className={styles.breakdown}>
            <div><dt>{t("coverage.language")}</dt><dd>{c.by_language.map((b) => `${b.key} ${b.count}`).join(" · ")}</dd></div>
            <div><dt>{t("coverage.provider")}</dt><dd>{c.by_provider_type.map((b) => `${providers[b.key] ?? b.key} ${b.count}`).join(" · ")}</dd></div>
          </dl>
        </details>
      </section>

      <section className={styles.section} aria-labelledby="impact-why">
        <div className={styles.sectionHeading}><h2 id="impact-why">{t("why.title")}</h2><Link href="/about">{t("aboutLink")}<ArrowUpRight size={16} aria-hidden /></Link></div>
        <ul className={styles.evidenceList}>{d.public_evidence.map((item) => <Evidence key={item.id} item={item} t={t} />)}</ul>
        {d.labour_context ? <p className={styles.small}>{t("why.labour", { month: d.labour_context.observed_month.slice(0, 7), rate: d.labour_context.unemployment_rate, date: d.labour_context.meta.sources[0]?.retrieved_at ?? "" })}</p> : null}
      </section>
    </>
  );
}

async function ImpactResults({ t }: { t: Translate }) {
  const provider = await getTranslations("pathway.catalogue.provider");
  const providers = Object.fromEntries(PROVIDERS.map((key) => [key, provider(key)]));
  const result = await fetchImpact();
  return result.ok ? <Body d={result.data} t={t} providers={providers} /> : <ErrorState failure={result} />;
}

/** Public impact evidence computed from synthetic profiles; results stream after the frame. */
export async function ImpactView() {
  const t = await getTranslations("impact");
  return (
    <div className="a-page">
      <SiteHeader />
      <main id="a-main" className={`a-wrap ${styles.page}`}>
        <header className={styles.intro}>
          <h1 className="a-display">{t("title")}</h1>
          <p>{t("honest")}</p>
        </header>
        <Suspense fallback={<div className={styles.loading} role="status" aria-live="polite"><span className="a-sr">{t("title")}</span><i /><i /><i /></div>}>
          <ImpactResults t={t} />
        </Suspense>
        <p className={styles.caveat}>{t("estimate")}</p>
      </main>
      <SiteFooter />
    </div>
  );
}
