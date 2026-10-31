import { BriefcaseBusiness } from "lucide-react";
import { getTranslations } from "next-intl/server";

import type { Schemas } from "@/lib/api";

/** Historical occupation-list context, not a live job vacancy or ranking component. */
export async function CriticalOccupationBadge({ badge }: { badge: Schemas["CriticalOccupationBadge"] | null | undefined }) {
  if (!badge) return null;
  const t = await getTranslations("matching");
  const source = badge.meta.sources[0];
  const label = t("criticalOccupation", { edition: badge.edition });
  return (
    <aside className="a-mycol" aria-label={label}>
      <span className="a-mycol-icon" aria-hidden><BriefcaseBusiness size={20} /></span>
      <div className="a-mycol-main">
        <p className="a-mycol-eyebrow">{label}</p>
        <p className="a-mycol-title">{badge.matched_title}</p>
        <p className="a-mycol-meta">{badge.occupation_label} · MASCO {badge.masco4d}</p>
      </div>
      <p className="a-mycol-note">{t("criticalOccupationNote")}</p>
      {source ? (
        <p className="a-mycol-source">
          {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.name}</a> : source.name}
          <time dateTime={source.retrieved_at}>{source.retrieved_at}</time>
        </p>
      ) : null}
    </aside>
  );
}
