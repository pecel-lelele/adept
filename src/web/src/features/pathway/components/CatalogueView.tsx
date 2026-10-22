import Link from "next/link";
import { ArrowUpRight, BookOpen, SlidersHorizontal } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { ApiError, MetaBar, PageHeader } from "@/components";
import { call, getApi, type Schemas } from "@/lib/api";
import { journeyHref } from "@/lib/navigation";

type Course = Schemas["Course"];

export type CatalogueQuery = {
  skill?: string;
  format?: Course["format"];
  audience?: "individual" | "corporate";
  provider_type?: Course["provider_type"];
  hrd_claimable?: boolean;
  max_cost_myr?: number;
};

const FORMATS = [
  "self_paced",
  "live_online",
  "in_person",
  "hybrid",
  "subscription",
] as const;
const PROVIDERS = [
  "mooc",
  "university",
  "industry_body",
  "professional_body",
  "private_provider",
  "government",
] as const;

async function CourseCard({ course }: { course: Course }) {
  const t = await getTranslations("pathway");
  const d = await getTranslations("common.design");
  const basis = course.price_basis ?? "per_course";
  const free = course.cost_myr === 0;
  return (
    <article className="a-card a-coursecard">
      <div className="a-coursecard-top">
        <span className="a-course-icon" aria-hidden>
          <BookOpen size={18} strokeWidth={1.6} />
        </span>
        <span className="a-eyebrow">
          {course.provider} · {t(`catalogue.format.${course.format ?? "self_paced"}`)}
        </span>
      </div>
      <h2>{course.title}</h2>
      <div className="a-chips">
        <span className="a-chip">{t("hours", { hours: course.hours })}</span>
        <span className="a-chip" data-tone={free ? "up" : undefined}>
          {free ? t("free") : t(`catalogue.price.${basis}`, { amount: course.cost_myr.toLocaleString("en-MY") })}
        </span>
        {course.hrd_claimable ? (
          <span className="a-chip" data-tone="dark">
            {t("hrdClaimable")}
          </span>
        ) : null}
      </div>
      <details className="a-disclosure">
        <summary>{d("courseDetails")}</summary>
        <div>
          <p>
            {t("catalogue.skills")}:{" "}
            {(course.skill_ids ?? []).map((x) => x.replaceAll("-", " ").replaceAll("_", " ")).join(", ")}
          </p>
          <p>
            {t("catalogue.level", { level: course.level ?? 1 })}
            {course.location ? " · " + course.location : ""}
          </p>
          {course.hrd_claimable ? (
            <p>
              {t("hrdClaimable")}. {course.hrd_note}
            </p>
          ) : null}
          {course.price_note ? <p>{course.price_note}</p> : null}
          {course.duration_note ? <p>{course.duration_note}</p> : null}
          <p className="a-muted">
            {course.source ? course.source.name + " · " : ""}
            {t("verified", { date: course.verified_at })}
          </p>
        </div>
      </details>
      <a href={course.url} target="_blank" rel="noreferrer" className="a-link" style={{ marginTop: "auto" }}>
        {d("visit")} <ArrowUpRight size={15} aria-hidden />
      </a>
    </article>
  );
}

/** Browse every course the pathway may recommend, with filters for learners and HR/L&D. */
export async function CatalogueView({
  query,
  basePath,
  context = {},
}: {
  query: CatalogueQuery;
  basePath: string;
  context?: Record<string, string>;
}) {
  const t = await getTranslations("pathway");
  const d = await getTranslations("common.design");
  const api = await getApi();
  const [result, all] = await Promise.all([
    call(api.GET("/api/v1/pathway/catalogue", { params: { query } })),
    call(api.GET("/api/v1/pathway/catalogue")),
  ]);
  const skills = all.ok ? [...new Set(all.data.courses.flatMap((c) => c.skill_ids ?? []))].sort() : [];
  const filtered = Object.values(query).some((v) => v !== undefined && v !== "");

  return (
    <div className="a-stack" style={{ gap: 24 }}>
      <PageHeader eyebrow={t("catalogue.title")} title={d("libraryBody")}>
        {result.ok ? <MetaBar meta={result.data.meta} /> : null}
      </PageHeader>
      <details className="a-card a-filters" open={filtered || undefined}>
        <summary>
          <SlidersHorizontal size={16} aria-hidden /> {d("filters")}
          {result.ok ? <span className="a-chip">{t("catalogue.count", { count: result.data.courses.length })}</span> : null}
        </summary>
        <form method="get" action={basePath} className="a-filter-grid">
          {Object.entries(context).map(([key, value]) => (
            <input key={key} type="hidden" name={key} value={value} />
          ))}
          <label className="a-field">
            {t("catalogue.skills")}
            <select name="skill" defaultValue={query.skill ?? ""} className="a-select">
              <option value="">{t("catalogue.any")}</option>
              {skills.map((x) => (
                <option key={x} value={x}>
                  {x}
                </option>
              ))}
            </select>
          </label>
          <label className="a-field">
            {t("catalogue.formatLabel")}
            <select name="format" defaultValue={query.format ?? ""} className="a-select">
              <option value="">{t("catalogue.any")}</option>
              {FORMATS.map((f) => (
                <option key={f} value={f}>
                  {t(`catalogue.format.${f}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="a-field">
            {t("catalogue.providerLabel")}
            <select name="provider_type" defaultValue={query.provider_type ?? ""} className="a-select">
              <option value="">{t("catalogue.any")}</option>
              {PROVIDERS.map((x) => (
                <option key={x} value={x}>
                  {t(`catalogue.provider.${x}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="a-field">
            {t("catalogue.audienceLabel")}
            <select name="audience" defaultValue={query.audience ?? ""} className="a-select">
              <option value="">{t("catalogue.any")}</option>
              <option value="individual">{t("catalogue.audience.individual")}</option>
              <option value="corporate">{t("catalogue.audience.corporate")}</option>
            </select>
          </label>
          <label className="a-field">
            {t("catalogue.maxCost")}
            <input type="number" name="max_cost_myr" min={0} step={50} defaultValue={query.max_cost_myr ?? ""} className="a-input" />
          </label>
          <label className="a-check" style={{ alignSelf: "end", minHeight: 46, alignItems: "center" }}>
            <input type="checkbox" name="hrd_claimable" value="true" defaultChecked={!!query.hrd_claimable} />
            {t("hrdClaimable")}
          </label>
          <div className="a-hero-actions" style={{ gridColumn: "1 / -1" }}>
            <button type="submit" className="a-btn is-small">
              {t("catalogue.apply")}
            </button>
            <Link href={journeyHref(basePath, new URLSearchParams(context))} className="a-link">
              {t("catalogue.reset")}
            </Link>
          </div>
        </form>
      </details>
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <div className="a-coursegrid">
          {result.data.courses.map((c) => (
            <CourseCard key={c.id} course={c} />
          ))}
        </div>
      )}
    </div>
  );
}
