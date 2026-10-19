import { getTranslations } from "next-intl/server";

export async function componentLabels(): Promise<Record<string, string>> {
  const t = await getTranslations("matching.component");
  return {
    skill_overlap: t("skill_overlap"),
    trend_outlook: t("trend_outlook"),
    interest_fit: t("interest_fit"),
  };
}
