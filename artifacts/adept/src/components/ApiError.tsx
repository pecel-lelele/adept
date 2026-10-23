import { getTranslations } from "next-intl/server";

import { EmptyState } from "./EmptyState";

export async function ApiError({ message }: { message: string }) {
  const t = await getTranslations("common.error");
  return <EmptyState title={t("apiTitle")} description={message} />;
}
