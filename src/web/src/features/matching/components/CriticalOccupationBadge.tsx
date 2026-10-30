import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import type { Schemas } from "@/lib/api";

export async function CriticalOccupationBadge({ badge }: { badge: Schemas["CriticalOccupationBadge"] | null | undefined }) {
  if (!badge) return null;
  const t = await getTranslations("matching");
  return (
    <div>
      <span className="a-chip" data-tone="up">{t("criticalOccupation", { edition: badge.edition })}</span>
      <p className="a-small a-muted">{badge.matched_title} · MASCO {badge.masco4d} · {badge.occupation_label}</p>
      <p className="a-small a-muted">{t("criticalOccupationNote")}</p>
      <MetaBar meta={badge.meta} />
    </div>
  );
}
