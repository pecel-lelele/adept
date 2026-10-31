import { useTranslations } from "next-intl";

import type { Source } from "@/lib/api";

/** A flat, compact source line (name and retrieval date), with no expander. */
export function SourceBadge({ sources }: { sources: Source[]; snapshotDate?: string }) {
  const t = useTranslations("common.source");
  return (
    <p className="a-sourcelink">
      <span>{t("label")}: </span>
      {sources.map((source, index) => (
        <span key={`${source.name}-${source.url}-${index}`}>
          {index ? " · " : ""}
          {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.name}</a> : source.name}
          {" "}
          <time dateTime={source.retrieved_at}>{source.retrieved_at}</time>
        </span>
      ))}
    </p>
  );
}
