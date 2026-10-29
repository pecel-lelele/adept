import Link from "next/link";
import { useTranslations } from "next-intl";

import type { Schemas } from "@/lib/api";

export function MatchImprovements({ items }: { items: Schemas["ScoreImprovement"][] }) {
  const t = useTranslations("matching");
  if (!items.length) return null;
  return (
    <div className="a-pad">
      <h3>{t("improvementsTitle")}</h3>
      <ul className="a-notes">
        {items.slice(0, 3).map((item) => (
          <li key={item.skill}>
            {item.label} · {t("scoreGain", { gain: (item.score_gain * 100).toFixed(1) })}{" "}
            {item.course_url && item.course_title ? (
              <Link href={item.course_url} target="_blank" rel="noreferrer">{item.course_title}</Link>
            ) : <span className="a-muted">{t("noClosingCourse")}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
