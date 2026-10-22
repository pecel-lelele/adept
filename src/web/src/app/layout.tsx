import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale } from "next-intl/server";
import type { ReactNode } from "react";

import "./globals.css";
import "./workspace.css";
import "./insight.css";
import "./adept.css";

export const metadata: Metadata = {
  title: "Adept · Aiversecity Future-Ready Workforce",
  description:
    "Future Skills Radar, role matching and reskilling pathways linked to the SDGs.",
};

export default async function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  const locale = await getLocale();
  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider>{children}</NextIntlClientProvider>
      </body>
    </html>
  );
}
