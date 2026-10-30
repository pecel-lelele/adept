"use client";

import { useSyncExternalStore } from "react";

import en from "../../messages/en/ui.json";
import ms from "../../messages/ms/ui.json";
import zh from "../../messages/zh/ui.json";
import { RouteErrorState } from "@/features/core/components/RouteErrorState";
import { defaultLocale, isLocale, LOCALE_COOKIE } from "@/lib/i18n/config";

import "./globals.css";
import "./adept.css";

const messages = { en, ms, zh };
const subscribe = () => () => {};
function browserLocale() {
  try {
    const cookie = document.cookie.split("; ").find((item) => item.startsWith(`${LOCALE_COOKIE}=`))?.split("=")[1];
    return isLocale(cookie) ? cookie : defaultLocale;
  } catch {
    return defaultLocale;
  }
}

export default function GlobalError({ retry }: { error: unknown; retry: () => void }) {
  const locale = useSyncExternalStore(subscribe, browserLocale, () => defaultLocale);
  const t = messages[locale].error;
  return (
    <html lang={locale}>
      <body>
        <RouteErrorState title={t.title} description={t.unexpected} home={t.home} retryLabel={t.retry} retry={retry} />
      </body>
    </html>
  );
}
