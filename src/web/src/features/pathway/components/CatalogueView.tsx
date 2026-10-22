import Link from "next/link";
import { BookOpen, ArrowUpRight } from "lucide-react";
import { getTranslations } from "next-intl/server";

import {
  ApiError,
  buttonVariants,
  MetaBar,
  PageHeader,
} from "@/components";
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

async function CourseCard({ course, index }: { course: Course; index: number }) {
  const t = await getTranslations("pathway"), d = await getTranslations("common.design");
  const basis = course.price_basis ?? "per_course";
  return <article className="course-card">
    <div className="course-cover" data-tone={index % 4} aria-hidden><span className="cover-tile"><BookOpen size={30} strokeWidth={1.2}/></span></div>
    <div className="course-body">
      <p className="course-provider">{course.provider} · {t(`catalogue.format.${course.format ?? "self_paced"}`)}</p>
      <h2>{course.title}</h2>
      <div className="course-facts"><span>{t("hours",{hours:course.hours})}</span><strong>{course.cost_myr === 0 ? t("free") : t(`catalogue.price.${basis}`,{amount:course.cost_myr.toLocaleString("en-MY")})}</strong></div>
      <details><summary>{d("courseDetails")}</summary><div className="course-detail-content">
        <p>{t("catalogue.skills")}: {(course.skill_ids ?? []).map(s => s.replaceAll("-"," ").replaceAll("_"," ")).join(", ")}</p>
        <p>{t("catalogue.level",{level:course.level ?? 1})}{course.location ? " · "+course.location : ""}</p>
        {course.hrd_claimable ? <p>{t("hrdClaimable")}. {course.hrd_note}</p> : null}
        {course.price_note ? <p>{course.price_note}</p> : null}
        {course.duration_note ? <p>{course.duration_note}</p> : null}
        <p>{course.source ? course.source.name+" · " : ""}{t("verified",{date:course.verified_at})}</p>
      </div></details>
      <a href={course.url} target="_blank" rel="noreferrer" className="course-footer">{d("visit")}<ArrowUpRight size={15} aria-hidden/></a>
    </div>
  </article>;
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
  const t = await getTranslations("pathway"), d = await getTranslations("common.design");
  const api = await getApi();
  const [result, all] = await Promise.all([
    call(api.GET("/api/v1/pathway/catalogue", { params: { query } })),
    call(api.GET("/api/v1/pathway/catalogue")),
  ]);
  const skills = all.ok
    ? [...new Set(all.data.courses.flatMap((c) => c.skill_ids ?? []))].sort()
    : [];
  const select = "rounded-md border bg-background px-2 py-1 text-sm";

  return (
    <section className="space-y-4">
      <PageHeader
        title={t("catalogue.title")}
        description={d("libraryBody")}
      />
      <details className="filter-panel" open={Object.values(query).some(v => v !== undefined && v !== "") || undefined}><summary>{d("filters")}</summary>
      <form
        method="get"
        action={basePath}
        className="flex flex-wrap items-end gap-2 text-sm"
      >
        {Object.entries(context).map(([key, value]) => (
          <input key={key} type="hidden" name={key} value={value} />
        ))}
        <label className="flex flex-col gap-1">
          {t("catalogue.skills")}
          <select
            name="skill"
            defaultValue={query.skill ?? ""}
            className={select}
          >
            <option value="">{t("catalogue.any")}</option>
            {skills.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          {t("catalogue.formatLabel")}
          <select
            name="format"
            defaultValue={query.format ?? ""}
            className={select}
          >
            <option value="">{t("catalogue.any")}</option>
            {FORMATS.map((f) => (
              <option key={f} value={f}>
                {t(`catalogue.format.${f}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          {t("catalogue.providerLabel")}
          <select
            name="provider_type"
            defaultValue={query.provider_type ?? ""}
            className={select}
          >
            <option value="">{t("catalogue.any")}</option>
            {PROVIDERS.map((p) => (
              <option key={p} value={p}>
                {t(`catalogue.provider.${p}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          {t("catalogue.audienceLabel")}
          <select
            name="audience"
            defaultValue={query.audience ?? ""}
            className={select}
          >
            <option value="">{t("catalogue.any")}</option>
            <option value="individual">
              {t("catalogue.audience.individual")}
            </option>
            <option value="corporate">
              {t("catalogue.audience.corporate")}
            </option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          {t("catalogue.maxCost")}
          <input
            type="number"
            name="max_cost_myr"
            min={0}
            step={50}
            defaultValue={query.max_cost_myr ?? ""}
            className={`${select} w-28`}
          />
        </label>
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            name="hrd_claimable"
            value="true"
            defaultChecked={!!query.hrd_claimable}
          />
          {t("hrdClaimable")}
        </label>
        <button type="submit" className={buttonVariants({ size: "sm" })}>
          {t("catalogue.apply")}
        </button>
        <Link
          href={journeyHref(basePath, new URLSearchParams(context))}
          className="text-sm underline"
        >
          {t("catalogue.reset")}
        </Link>
      </form></details>
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <>
          <MetaBar meta={result.data.meta} />
          <p className="text-sm text-muted-foreground">
            {t("catalogue.count", { count: result.data.courses.length })}
          </p>
          <div className="catalogue-grid">
            {result.data.courses.map((c, index) => (
              <CourseCard key={c.id} course={c} index={index} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
