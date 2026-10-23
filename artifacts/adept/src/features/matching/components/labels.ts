import { getTranslations } from "@/lib/next-compat/intl";

export async function componentLabels(): Promise<Record<string, string>> {
  const t = await getTranslations("matching.component");
  return {
    skill_overlap: t("skill_overlap"),
    trend_outlook: t("trend_outlook"),
    interest_fit: t("interest_fit"),
    sdg_impact: t("sdg_impact"),
  };
}
