import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { Schemas } from "@/lib/api";

/** Only actionable skills and verified catalogue-course links, not counterfactual arithmetic. */
export function MatchImprovements({ items, hideTitle = false, fallback }: { items: Schemas["ScoreImprovement"][]; hideTitle?: boolean; fallback?: string }) {
  const t = useTranslations("matching");
  if (!items.length) return fallback ? <p className="a-muted a-small">{fallback}</p> : null;
  return (
    <section className="a-improve" aria-label={t("improvementsTitle")}>
      {hideTitle ? null : <h3>{t("improvementsTitle")}</h3>}
      <ul>
        {items.slice(0, 3).map((item) => (
          <li key={item.skill}>
            <strong>{item.label}</strong>
            {item.course_url && item.course_title ? (
              <Link href={item.course_url} target="_blank" rel="noreferrer">{item.course_title}<ArrowUpRight size={14} aria-hidden /></Link>
            ) : <span className="a-improve-none">{t("noClosingCourse")}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}
