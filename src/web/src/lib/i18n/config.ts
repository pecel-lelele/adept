export const locales = ["en", "ms", "zh"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";
export const LOCALE_COOKIE = "NEXT_LOCALE";

export const localeLabels: Record<Locale, string> = {
  en: "English",
  ms: "Bahasa Melayu",
  zh: "中文",
};

/** One JSON file per namespace per locale in src/web/messages/<locale>/<namespace>.json. */
export const namespaces = [
  "common",
  "trends",
  "scenarios",
  "profile",
  "matching",
  "pathway",
  "sdg",
  "org",
  "guardrails",
  "ui",
  "jobs",
  "privacy",
] as const;

export function isLocale(value: string | undefined): value is Locale {
  return locales.includes(value as Locale);
}
