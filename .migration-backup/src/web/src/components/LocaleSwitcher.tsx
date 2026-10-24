"use client";

import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useTransition } from "react";

import { LOCALE_COOKIE, localeLabels, locales, type Locale } from "@/lib/i18n/config";

const SHORT: Record<Locale, string> = { en: "EN", ms: "BM", zh: "中文" };

function saveLocale(value: string) {
  document.cookie = `${LOCALE_COOKIE}=${value}; path=/; max-age=31536000; samesite=lax`;
}

/** Language control. `segmented` (default) is the pill of EN / BM / 中文 from the partner
 *  design; `select` is a compact dropdown for tight spots. */
export function LocaleSwitcher({ variant = "segmented" }: { variant?: "segmented" | "select" }) {
  const t = useTranslations("common.locale");
  const locale = useLocale();
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  // Fade the page while the new language renders, instead of swapping text abruptly.
  useEffect(() => {
    const root = document.documentElement;
    if (pending) root.dataset.localeSwitching = "true";
    else delete root.dataset.localeSwitching;
  }, [pending]);
  const choose = (value: string) => {
    saveLocale(value);
    startTransition(() => router.refresh());
  };

  if (variant === "select") {
    return (
      <select
        aria-label={t("label")}
        value={locale}
        onChange={(e) => choose(e.target.value)}
        className="a-locale-select"
      >
        {locales.map((l) => (
          <option key={l} value={l}>
            {localeLabels[l]}
          </option>
        ))}
      </select>
    );
  }
  return (
    <div className="a-seg a-locale" role="group" aria-label={t("label")}>
      {locales.map((l) => (
        <button
          key={l}
          type="button"
          aria-pressed={locale === l}
          lang={l}
          title={localeLabels[l]}
          onClick={() => locale !== l && choose(l)}
        >
          {SHORT[l]}
        </button>
      ))}
    </div>
  );
}
