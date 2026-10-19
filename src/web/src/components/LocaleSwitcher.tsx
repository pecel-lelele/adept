"use client";

import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";

import { LOCALE_COOKIE, localeLabels, locales } from "@/lib/i18n/config";

export function LocaleSwitcher() {
  const t = useTranslations("common.locale");
  const locale = useLocale();
  const router = useRouter();

  return (
    <select
      aria-label={t("label")}
      value={locale}
      onChange={(e) => {
        document.cookie = `${LOCALE_COOKIE}=${e.target.value}; path=/; max-age=31536000; samesite=lax`;
        router.refresh();
      }}
      className="rounded-md border bg-background px-2 py-1 text-xs"
    >
      {locales.map((l) => (
        <option key={l} value={l}>
          {localeLabels[l]}
        </option>
      ))}
    </select>
  );
}
