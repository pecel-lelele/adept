import { getTranslations } from "next-intl/server";

import { RouteErrorState } from "@/features/core/components/RouteErrorState";

export default async function NotFound() {
  const t = await getTranslations("ui.error");
  return <RouteErrorState title={t("notFoundTitle")} description={t("notFoundHint")} home={t("home")} />;
}
