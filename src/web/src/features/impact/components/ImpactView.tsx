import { getTranslations } from "next-intl/server";

import { ErrorState, MetaBar } from "@/components";
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

function Card(props: { label: string; value: string; note: string; formula: string; source: string }) {
  return (
    <section className="a-card">
      <h2 className="a-small">{props.label}</h2>
      <p className={styles.value}>{props.value}</p>
      <p>{props.note}</p>
      <p className={styles.small}>{props.formula}</p>
      <p className={styles.small}>{props.source}</p>
    </section>
  );
}

function Evidence({ item, t }: { item: EvidenceItem; t: Translate }) {
  return (
    <section className="a-card">
      <span className="a-chip">{item.scope}</span>
      <p className={styles.value}>{item.figure}</p>
      <p>{item.claim}</p>
      <p className={styles.quote}>&ldquo;{item.quote}&rdquo;</p>
      <p className={styles.small}>
        <a className="a-link" href={item.url} target="_blank" rel="noreferrer">
          {item.publisher}
        </a>{" "}
        · {t("retrieved", { date: item.retrieved_at })}
        {item.published_at ? ` · ${t("published", { date: item.published_at })}` : ""}
      </p>
      {isFeature(item.feature) ? <p>{t(`feature.${item.feature}`)}</p> : null}
    </section>
  );
}

function Body({ d, t, providers }: { d: ImpactSummary; t: Translate; providers: Record<string, string> }) {
  const moderate = d.aggregates.find((a) => a.scenario === "moderate");
  const fast = d.aggregates.find((a) => a.scenario === "fast");
  if (!moderate || !fast) return null;
  const catalogue = t("source.catalogue", { date: d.meta.sources[0]?.retrieved_at ?? "" });
  const trend = t("source.trend", { date: d.meta.snapshot_date });
  const both = `${catalogue} · ${trend}`;
  const c = d.catalogue;
  return (
    <>
      <div className={styles.grid}>
        <Card
          label={t("free.label")}
          value={pct(moderate.median_free_course_share)}
          note={t("free.note", {
            hours: pct(moderate.median_free_hours_share),
            hrd: pct(moderate.median_hrd_course_share),
          })}
          formula={t("free.formula")}
          source={catalogue}
        />
        <Card
          label={t("hours.label")}
          value={num(moderate.median_total_hours)}
          note={t("hours.note", { fast: num(fast.median_total_hours) })}
          formula={t("hours.formula")}
          source={both}
        />
        <Card
          label={t("sdg.label")}
          value={num(moderate.median_sdg_target_count)}
          note={t("sdg.note")}
          formula={t("sdg.formula")}
          source={both}
        />
        <Card
          label={t("scenario.label")}
          value={num(moderate.median_top5_changed)}
          note={t("scenario.note", { count: d.personas.filter((p) => p.top_role_changed).length })}
          formula={t("scenario.formula")}
          source={trend}
        />
        <Card
          label={t("fairness.label")}
          value={String(d.fairness.max_rank_change)}
          note={t("fairness.note", {
            variants: d.fairness.variants_tested,
            passed: String(d.fairness.guardrail_report_passed),
          })}
          formula={t("fairness.formula")}
          source={trend}
        />
        <Card
          label={t("coverage.label")}
          value={String(c.course_count)}
          note={t("coverage.note", {
            roles: c.role_count,
            skills: c.skill_count,
            fresh: pct(c.verified_recent_share),
            days: c.verified_window_days,
            date: c.as_of,
          })}
          formula={t("coverage.formula")}
          source={catalogue}
        />
        <Card label={t("catalogueFree.label")} value={pct(c.free_course_share)}
          note={t("catalogueFree.note", { count: c.free_course_count, hours: num(c.free_hours) })}
          formula={t("catalogueFree.formula")} source={catalogue} />
        <Card label={t("catalogueSdg.label")} value={String(c.sdg_target_count)}
          note={t("catalogueSdg.note", { links: c.role_sdg_link_count, targets: c.target_role_count })}
          formula={t("catalogueSdg.formula")} source={catalogue} />
      </div>

      <details className={styles.details}>
        <summary>{t("personas.title")}</summary>
        <div className={styles.scroll}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>{t("personas.persona")}</th>
                <th>{t("personas.role")}</th>
                <th>{t("personas.hours")}</th>
                <th>{t("personas.free")}</th>
                <th>{t("personas.hrd")}</th>
                <th>{t("personas.sdg")}</th>
                <th>{t("personas.changed")}</th>
              </tr>
            </thead>
            <tbody>
              {d.personas.map((p) => (
                <tr key={p.persona_id}>
                  <td>{p.persona_id}</td>
                  <td>{p.moderate.top_role_label}</td>
                  <td>{num(p.moderate.total_hours)}</td>
                  <td>{pct(p.moderate.free_course_share)}</td>
                  <td>{pct(p.moderate.hrd_course_share)}</td>
                  <td>{p.moderate.sdg_target_count}</td>
                  <td>{p.top5_changed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className={styles.small}>{t("personas.note")}</p>
      </details>

      <details className={styles.details}>
        <summary>{t("coverage.title")}</summary>
        <p>
          <strong>{t("coverage.language")}:</strong> {c.by_language.map((b) => `${b.key} ${b.count}`).join(" · ")}
        </p>
        <p>
          <strong>{t("coverage.provider")}:</strong>{" "}
          {c.by_provider_type.map((b) => `${providers[b.key] ?? b.key} ${b.count}`).join(" · ")}
        </p>
      </details>

      <h2>{t("why.title")}</h2>
      <p className="a-muted">{t("why.lead")}</p>
      <div className={styles.grid}>
        {d.public_evidence.map((item) => (
          <Evidence key={item.id} item={item} t={t} />
        ))}
      </div>
      {d.labour_context ? (
        <p className={styles.small}>
          {t("why.labour", {
            month: d.labour_context.observed_month.slice(0, 7),
            rate: d.labour_context.unemployment_rate,
            date: d.labour_context.meta.sources[0]?.retrieved_at ?? "",
          })}
        </p>
      ) : null}
    </>
  );
}

/** Public impact evidence (F8): figures computed live from the catalogue and trend snapshot. */
export async function ImpactView() {
  const t = await getTranslations("impact");
  const provider = await getTranslations("pathway.catalogue.provider");
  const providers = Object.fromEntries(PROVIDERS.map((key) => [key, provider(key)]));
  const result = await fetchImpact();
  return (
    <div className="a-page">
      <SiteHeader />
      <main id="a-main" className="a-wrap a-section">
        <span className="a-eyebrow is-square">{t("eyebrow")}</span>
        <h1 className="a-display">{t("title")}</h1>
        {result.ok ? (
          <>
            <p className="a-hero2-lead">{t("basis", { count: result.data.personas.length })}</p>
            <MetaBar meta={result.data.meta} />
            {result.data.meta.observed_to && Date.parse(result.data.meta.snapshot_date) - Date.parse(result.data.meta.observed_to) > 60 * 864e5 ? (
              <p className="a-notice">{t("historical", { from: result.data.meta.observed_from ?? result.data.meta.observed_to, to: result.data.meta.observed_to })}</p>
            ) : null}
            <Body d={result.data} t={t} providers={providers} />
          </>
        ) : (
          <ErrorState failure={result} />
        )}
        <p className={styles.honest}>{t("honest")}</p>
        <p className={styles.small}>{t("estimate")}</p>
      </main>
      <SiteFooter />
    </div>
  );
}
