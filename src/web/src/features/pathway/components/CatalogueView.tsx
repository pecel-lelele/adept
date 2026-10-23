import Form from "next/form";
import Link from "next/link";
import { ArrowUpRight, BadgeCheck, BookOpen, Clock3, Gift, SlidersHorizontal } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { ApiError, Kpis, MetaBar, PageHeader } from "@/components";
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
  const free = course.cost_myr === 0 && course.price_status !== "certificate_price_unknown";
  return (
    <article className="a-card a-coursecard">
      <div className="a-coursecard-top">
        <span className="a-course-icon" aria-hidden>
          <BookOpen size={18} strokeWidth={1.6} />
        </span>
        <span className="a-coursecard-provider">
          <strong>{course.provider}</strong>
          <small>{t(`catalogue.format.${course.format ?? "self_paced"}`)}</small>
        </span>
      </div>
      <h2>{course.title}</h2>
      <div className="a-chips">
        <span className="a-chip">
          <Clock3 size={12} aria-hidden /> {t("hours", { hours: course.hours })}
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
      {course.certificate_note ? <p className="a-small a-muted">{course.certificate_note}</p> : null}
      <footer className="a-coursecard-foot">
        <strong data-free={free || undefined}>
          {course.price_status === "certificate_price_unknown" ? t("certificateQuote") : free ? t("free") : t(`catalogue.price.${basis}`, { amount: course.cost_myr.toLocaleString("en-MY") })}
        </strong>
        <a href={course.url} target="_blank" rel="noreferrer" className="a-link">
          {d("visit")} <ArrowUpRight size={15} aria-hidden />
        </a>
      </footer>
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
  const tp = await getTranslations("ui.page");
  const api = await getApi();
  const [result, all] = await Promise.all([
    call(api.GET("/api/v1/pathway/catalogue", { params: { query } })),
    call(api.GET("/api/v1/pathway/catalogue")),
  ]);
  const skills = all.ok ? [...new Set(all.data.courses.flatMap((c) => c.skill_ids ?? []))].sort() : [];
  const every = all.ok ? all.data.courses : [];
  const shown = result.ok ? result.data.courses.length : 0;

  return (
    <div className="a-view">
      <PageHeader eyebrow={d("options")} title={t("catalogue.title")} description={t("catalogue.description")}>
        {result.ok ? <MetaBar meta={result.data.meta} /> : null}
      </PageHeader>
      <Kpis
        items={[
          { label: tp("kCourses"), value: every.length, icon: <BookOpen size={15} />, note: tp("kProviders", { count: new Set(every.map((c) => c.provider)).size }) },
          { label: tp("kFree"), value: every.filter((c) => c.cost_myr === 0 && c.price_status === "listed").length, icon: <Gift size={15} />, tone: "up", note: tp("kFreeNote") },
          { label: tp("kHrd"), value: every.filter((c) => c.hrd_claimable).length, icon: <BadgeCheck size={15} />, note: tp("kHrdNote") },
          { label: tp("kSelfPaced"), value: every.filter((c) => c.format === "self_paced").length, icon: <Clock3 size={15} />, note: tp("kSelfPacedNote") },
        ]}
      />
      <section className="a-card a-filters" aria-labelledby="h-filters">
        <div className="a-card-head">
          <h2 id="h-filters">
            <SlidersHorizontal size={16} aria-hidden /> {d("filters")}
          </h2>
        </div>
        <Form action={basePath} className="a-filter-grid">
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
          <div className="a-filter-actions">
            <button type="submit" className="a-btn is-small">
              {t("catalogue.apply")}
            </button>
            <Link href={journeyHref(basePath, new URLSearchParams(context))} className="a-link">
              {t("catalogue.reset")}
            </Link>
          </div>
        </Form>
      </section>
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <>
          <p className="a-results-count">{t("catalogue.count", { count: shown })}</p>
          <div className="a-coursegrid">
            {result.data.courses.map((c) => (
              <CourseCard key={c.id} course={c} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
