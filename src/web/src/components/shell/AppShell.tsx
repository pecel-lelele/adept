import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";

import { individualNav } from "@/config/navigation";

import { Shell } from "./Shell";

/** Individual mode (/app): working adults, graduates, career switchers. */
export async function AppShell({ children }: { children: ReactNode }) {
  const t = await getTranslations("common.landing");
  return (
    <Shell nav={individualNav} modeLabel={t("individual")}>
      {children}
    </Shell>
  );
}
