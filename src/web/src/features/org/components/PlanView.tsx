import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { StepTrack } from "@/components/viz";
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
  const tu = await getTranslations("ui.org");
  const tn = await getTranslations("ui.nav");
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
      <div className="a-pagehead"><h1 className="a-h1">{tn("teamPlan")}</h1></div>
      {gaps.ok ? (
        <form
          action="/org/plan"
          className="a-card"
          style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "end", marginBottom: 20 }}
        >
          <input type="hidden" name="scenario" value={scenario} />
          <label className="a-field" style={{ minWidth: 240 }}>
            {tn("roles")}
            <select
              name="role"
              defaultValue={
                roleId ?? (result.ok ? result.data.target_role_id : "")
              }
              className="a-select"
            >
              {gaps.data.role_ids.map((id) => (
                <option key={id} value={id}>
                  {gaps.data.role_labels?.[id] ?? id}
                </option>
              ))}
            </select>
          </label>
          <button className="a-btn">{tn("teamPlan")} →</button>
        </form>
      ) : null}
      {!result.ok ? (
        <ErrorState failure={result} />
      ) : (
        <div className="space-y-3">
          <section className="a-card">
            <div className="a-card-head">
              <h2>{result.data.target_role_label}</h2>
              <span className="a-chip">
                {tu("planBody", {
                  steps: result.data.steps.length,
                  weeks: result.data.total_weeks,
                  people: result.data.assigned_member_ids.length,
                })}
              </span>
            </div>
            <StepTrack
              steps={result.data.steps.slice(0, 8).map((s, i) => ({
                id: s.skill_id,
                label: s.skill_label || s.skill_id,
                state: i === 0 ? "current" : "todo",
              }))}
            />
          </section>
          <MetaBar meta={result.data.meta} />
          <PathwaySteps steps={result.data.steps} memberNames={names} />
        </div>
      )}
    </section>
  );
}
