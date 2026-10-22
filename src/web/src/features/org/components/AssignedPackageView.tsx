import { getTranslations } from "next-intl/server";
import { call, getApi } from "@/lib/api";
import { ActionForm } from "@/features/pathway/components/ActionForm";
import { acceptPackageAction } from "../funding-actions";

export async function AssignedPackageView() {
  const api = await getApi();
  const result = await call(api.GET("/api/v1/org/packages/assigned"));
  if (!result.ok || !result.data) return null;
  const t = await getTranslations("org.packages");
  const p = result.data;
  return <section className="a-card">
    <h2>{t("assigned")}: {p.pathway.role_label}</h2>
    <p>{t(`kind.${p.kind}`)} · RM {p.pathway.total_cost_myr} · {t("weeks", { count: p.pathway.total_weeks })}</p>
    <p>{t("acceptHint")}</p>
    <details className="a-disclosure"><summary>{t("preview")}</summary>
      <ol>{p.pathway.steps.map(s => <li key={s.order}>{s.skill_label}: {s.courses.map(c => c.title).join(", ")}</li>)}</ol>
      <p>{t("unmet")}: {(p.pathway.unmet ?? []).map(u => u.label).join(", ") || "—"}</p>
    </details>
    <ActionForm action={acceptPackageAction} label={t("accept")} fields={{ token: p.token }} />
  </section>;
}
