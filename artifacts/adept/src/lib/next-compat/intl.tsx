import { useEffect, useMemo, type ReactNode } from "react";
import { createTranslator, IntlProvider, useTranslations, type Messages, type NamespaceKeys, type NestedKeyOf } from "use-intl";

import { defaultLocale, isLocale, LOCALE_COOKIE, namespaces, type Locale } from "@/lib/i18n/config";

import { useGeneration } from "./router";

export { useLocale, useTranslations } from "use-intl";

const files = import.meta.glob<{ default: Record<string, unknown> }>("../../../messages/*/*.json", { eager: true });

const TIME_ZONE = "Asia/Kuala_Lumpur";

function readLocale(): Locale {
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${LOCALE_COOKIE}=`));
  const value = match ? decodeURIComponent(match.split("=")[1] ?? "") : undefined;
  return isLocale(value) ? value : defaultLocale;
}

function loadMessages(locale: Locale): Record<string, Record<string, unknown>> {
  return Object.fromEntries(
    namespaces.map((ns) => [ns, files[`../../../messages/${locale}/${ns}.json`]?.default ?? {}]),
  );
}

/** Equivalent of next-intl/server getLocale (cookie-based, no URL prefix). */
export async function getLocale(): Promise<Locale> {
  return readLocale();
}

/** Equivalent of next-intl/server getTranslations for async views. */
export async function getTranslations<NS extends NamespaceKeys<Messages, NestedKeyOf<Messages>> = never>(
  namespace?: NS,
): Promise<ReturnType<typeof useTranslations<NS>>> {
  const locale = readLocale();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const t = createTranslator({ locale, messages: loadMessages(locale) as any, namespace: namespace as any, timeZone: TIME_ZONE });
  return t as unknown as ReturnType<typeof useTranslations<NS>>;
}

/** Re-reads the locale cookie on every router refresh (LocaleSwitcher). */
export function AppIntlProvider({ children }: { children: ReactNode }) {
  const generation = useGeneration();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const locale = useMemo(() => readLocale(), [generation]);
  const messages = useMemo(() => loadMessages(locale), [locale]);
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
  return (
    <IntlProvider locale={locale} messages={messages} timeZone={TIME_ZONE}>
      {children}
    </IntlProvider>
  );
}
