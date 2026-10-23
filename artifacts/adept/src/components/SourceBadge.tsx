import { useTranslations } from "@/lib/next-compat/intl";

import type { Source } from "@/lib/api";

/** Shows where a recommendation comes from and how fresh it is. */
export function SourceBadge({ sources, snapshotDate }: { sources: Source[]; snapshotDate?: string }) {
  const t = useTranslations("common.source");
  return (
    <span className="a-source">
      <b>{t("label")}:</b>
      {sources.map((s) =>
        s.url ? (
          <a key={s.name} href={s.url} target="_blank" rel="noreferrer">
            {s.name}
          </a>
        ) : (
          <span key={s.name}>{s.name}</span>
        ),
      )}
      <span>· {t("asOf", { date: snapshotDate ?? sources[0]?.retrieved_at ?? "?" })}</span>
    </span>
  );
}
