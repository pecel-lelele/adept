import { getTranslations } from "next-intl/server";

import type { Schemas } from "@/lib/api";

/** Use the server's deduplicated totals: a course can teach more than one skill. */
export async function PlanTotals({ plan }: { plan: Schemas["Pathway"] }) {
  const t = await getTranslations("pathway");
  return (
    <footer className="a-card" aria-label={t("summary.title")}>
      <h2>{t("summary.title")}</h2>
      <p>{t("totalWeeks", { weeks: plan.total_weeks })} · {t("summary.totalHours", { hours: plan.total_hours ?? 0 })}</p>
      <strong>{t("summary.listPrice", { amount: plan.total_cost_myr ?? 0 })}</strong>
      <p className="a-small a-muted">{t("summary.hrdNote")}</p>
      <p className="a-small a-muted">{t("estimateNote")}</p>
    </footer>
  );
}
