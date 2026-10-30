"use client";

import { useTranslations } from "next-intl";

import { RouteErrorState } from "@/features/core/components/RouteErrorState";

export default function ErrorPage({ retry }: { error: unknown; retry: () => void }) {
  const t = useTranslations("ui.error");
  return <RouteErrorState title={t("title")} description={t("unexpected")} home={t("home")} retryLabel={t("retry")} retry={retry} />;
}
