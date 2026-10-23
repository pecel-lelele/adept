import { asyncView } from "@/lib/next-compat/async-view";
import { getTranslations } from "@/lib/next-compat/intl";

import { EmptyState } from "./EmptyState";

async function ApiErrorAsync({ message }: { message: string }) {
  const t = await getTranslations("common.error");
  return <EmptyState title={t("apiTitle")} description={message} />;
}

export const ApiError = asyncView(ApiErrorAsync);
