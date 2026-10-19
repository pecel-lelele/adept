import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";

import { defaultLocale, isLocale, LOCALE_COOKIE, namespaces } from "./config";

// No locale prefix in URLs: the locale comes from a cookie set by the LocaleSwitcher.
export default getRequestConfig(async () => {
  const value = (await cookies()).get(LOCALE_COOKIE)?.value;
  const locale = isLocale(value) ? value : defaultLocale;
  const entries = await Promise.all(
    namespaces.map(
      async (ns) => [ns, (await import(`../../../messages/${locale}/${ns}.json`)).default] as const,
    ),
  );
  return { locale, messages: Object.fromEntries(entries), timeZone: "Asia/Kuala_Lumpur" };
});
