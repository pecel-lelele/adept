import { getTranslations } from "next-intl/server";

import { ApiError, MetaBar, PageHeader } from "@/components";
import { PathwaySteps } from "@/features/pathway";
import type { ScenarioId } from "@/lib/api";

import { fetchGaps, fetchMembers, fetchPlan } from "../api";

export async function PlanView({
  scenario,
  roleId,
}: {
  scenario: ScenarioId;
  roleId?: string;
}) {
  const t = await getTranslations("org");
  const [result, members, gaps] = await Promise.all([
    fetchPlan(scenario, roleId),
    fetchMembers(),
    fetchGaps(scenario),
  ]);
  const names = Object.fromEntries(
    (members.ok ? members.data.members : []).map((m) => [m.id, m.display_name]),
  );
  return (
    <section>
      <PageHeader title={t("planTitle")} />
      {gaps.ok ? (
        <form
          action="/org/plan"
          className="mb-5 flex flex-wrap items-end gap-3 text-sm"
        >
          <input type="hidden" name="scenario" value={scenario} />
          <label className="grid gap-2">
            Target role
            <select
              name="role"
              defaultValue={
                roleId ?? (result.ok ? result.data.target_role_id : "")
              }
              className="rounded-lg border p-2"
            >
              {gaps.data.role_ids.map((id) => (
                <option key={id} value={id}>
                  {id.replaceAll("-", " ")}
                </option>
              ))}
            </select>
          </label>
          <button className="workspace-button">Preview group plan →</button>
        </form>
      ) : null}
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <div className="space-y-3">
          <p className="text-sm">
            {t("target", { role: result.data.target_role_id })} ·{" "}
            {t("assigned", { count: result.data.assigned_member_ids.length })}
          </p>
          <MetaBar meta={result.data.meta} />
          <PathwaySteps steps={result.data.steps} memberNames={names} />
        </div>
      )}
    </section>
  );
}
