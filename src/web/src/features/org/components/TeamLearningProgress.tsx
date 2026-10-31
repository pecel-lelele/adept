import { getTranslations } from "next-intl/server";

import type { Schemas } from "@/lib/api";

/** Course completion is self-reported; a separate evidence gate controls the skills heatmap. */
export async function TeamLearningProgress({ rows }: { rows: Schemas["TeamSkillProgress"][] }) {
  const t = await getTranslations("org.learning");
  return (
    <section className="a-card">
      <h2>{t("title")}</h2>
      <p className="a-small a-muted">{t("description")}</p>
      {rows.length ? <div className="a-table-wrap"><table className="a-table">
        <thead><tr><th scope="col">{t("skill")}</th><th scope="col">{t("courses")}</th><th scope="col">{t("completion")}</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.skill_id}>
          <th scope="row">{row.label}</th>
          {row.suppressed || row.completed_courses == null || row.planned_courses == null ? (
            <td colSpan={2}>{t("suppressed")}</td>
          ) : <>
            <td>{row.completed_courses} / {row.planned_courses}</td>
            <td><progress max={Math.max(1, row.planned_courses)} value={row.completed_courses} aria-label={row.label} /> {Math.round(100 * row.completed_courses / Math.max(1, row.planned_courses))}%</td>
          </>}
        </tr>)}</tbody>
      </table></div> : <p className="a-muted">{t("empty")}</p>}
    </section>
  );
}
