"use client";

import { Plus, Search } from "lucide-react";

import type { Schemas } from "@/lib/api";
import { useTranslations } from "next-intl";

/** Unverified wording stays in this upload's memory, outside saved skills and scores. */
export function CvReview({ terms, truncated, matchedCount, onSearch, suggestions = [], onAdd, added }: {
  terms: string[];
  truncated: boolean;
  matchedCount: number;
  onSearch?: (term: string) => void;
  /** Closest catalogue skill by meaning (embeddings), for some terms. Proposals only. */
  suggestions?: Schemas["SkillSuggestion"][];
  onAdd?: (skillId: string) => void;
  added?: ReadonlySet<string>;
}) {
  const t = useTranslations("ui.cvReview");
  const byTerm = new Map(suggestions.map((s) => [s.term, s]));
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
            {terms.map((term) => {
              const s = byTerm.get(term);
              return (
              <li key={term}>
                <span>
                  {term}
                  {s ? (
                    <small className="a-muted a-suggest">
                      {" "}
                      {t("closest", { label: s.label, pct: Math.round(s.similarity * 100) })}
                    </small>
                  ) : null}
                </span>
                {s && onAdd ? (
                  added?.has(s.skill_id) ? (
                    <span className="a-chip" data-tone="up">{t("added")}</span>
                  ) : (
                    <button type="button" className="a-link" onClick={() => onAdd(s.skill_id)} aria-label={t("addFor", { label: s.label, term })}>
                      <Plus size={14} aria-hidden /> {t("add", { label: s.label })}
                    </button>
                  )
                ) : onSearch ? (
                  <button type="button" className="a-link" onClick={() => onSearch(term)} aria-label={t("searchFor", { term })}>
                    <Search size={14} aria-hidden /> {t("search")}
                  </button>
                ) : null}
              </li>
              );
            })}
          </ul>
          <p className="a-small a-muted">{t("notSaved")}</p>
        </>
      ) : null}
    </section>
  );
}
