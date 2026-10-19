import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";

import { organisationNav } from "@/config/navigation";

import { Shell } from "./Shell";

/** Organisation mode (/org): HR / L&D managers and career centres. */
export async function OrgShell({ children }: { children: ReactNode }) {
  const t = await getTranslations("common.landing");
  return (
    <Shell nav={organisationNav} modeLabel={t("organisation")}>
      {children}
    </Shell>
  );
}
