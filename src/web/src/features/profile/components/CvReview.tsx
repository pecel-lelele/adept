"use client";

import { Search } from "lucide-react";
import { useTranslations } from "next-intl";

/** Unverified wording stays in this upload's memory, outside saved skills and scores. */
export function CvReview({ terms, truncated, matchedCount, onSearch }: {
  terms: string[];
  truncated: boolean;
  matchedCount: number;
  onSearch?: (term: string) => void;
}) {
  const t = useTranslations("ui.cvReview");
  return (
    <section className="a-cv-review" aria-label={t("title")}>
      <p className="a-small a-muted">{t("scope")}</p>
      {!matchedCount ? <p className="a-small">{t("none")}</p> : null}
      {truncated ? <p className="a-notice" role="status">{t("truncated")}</p> : null}
      {terms.length ? (
        <>
          <h3>{t("title")}</h3>
          <p className="a-small a-muted">{t("body")}</p>
          <ul>
            {terms.map((term) => (
              <li key={term}>
                <span>{term}</span>
                {onSearch ? (
                  <button type="button" className="a-link" onClick={() => onSearch(term)} aria-label={t("searchFor", { term })}>
                    <Search size={14} aria-hidden /> {t("search")}
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
          <p className="a-small a-muted">{t("notSaved")}</p>
        </>
      ) : null}
    </section>
  );
}
