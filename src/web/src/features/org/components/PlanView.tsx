import { ArrowRight, CalendarRange, ListOrdered, Users } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Kpis, MetaBar, PageHeader } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { StepTrack } from "@/components/viz";
import { PathwaySteps } from "@/features/pathway";
import type { ScenarioId } from "@/lib/api";

import { fetchGaps, fetchMembers, fetchPlan } from "../api";

/**
 * Step 4 for organisations: one shared plan towards a target role (default: the largest team
 * gap; the manager can pick another). Each step lists the members it applies to.
 */
export async function PlanView({ scenario, roleId }: { scenario: ScenarioId; roleId?: string }) {
  const tu = await getTranslations("ui.org");
  const tn = await getTranslations("ui.nav");
  const tp = await getTranslations("ui.page");
  const [result, members, gaps] = await Promise.all([fetchPlan(scenario, roleId), fetchMembers(), fetchGaps(scenario)]);
  const names = Object.fromEntries((members.ok ? members.data.members : []).map((m) => [m.id, m.display_name]));
  const picker = gaps.ok ? (
    <form action="/org/plan" className="a-rolepick">
      <input type="hidden" name="scenario" value={scenario} />
      <label className="a-inline-select">
        {tp("targetRole")}
        <select name="role" defaultValue={roleId ?? (result.ok ? result.data.target_role_id : "")} className="a-select is-small">
          {gaps.data.role_ids.map((id) => (
            <option key={id} value={id}>
              {gaps.data.role_labels?.[id] ?? id}
            </option>
          ))}
        </select>
      </label>
      <button className="a-btn is-small">
        {tp("showPlan")} <ArrowRight size={14} aria-hidden />
      </button>
    </form>
  ) : null;

  return (
    <div className="a-view">
      <PageHeader
        eyebrow={tp("stepOf", { step: 4 })}
        title={result.ok ? result.data.target_role_label : tn("teamPlan")}
        description={tp("teamPlanDesc")}
        actions={picker}
      >
        {result.ok ? <MetaBar meta={result.data.meta} /> : null}
      </PageHeader>
      {!result.ok ? (
        <ErrorState failure={result} />
      ) : (
        <>
          <Kpis
            items={[
              { label: tp("kSteps2"), value: result.data.steps.length, icon: <ListOrdered size={15} /> },
              { label: tp("kDuration"), value: result.data.total_weeks, unit: tp("weeksUnit"), icon: <CalendarRange size={15} />, note: tp("estimate") },
              { label: tp("kPeople"), value: result.data.assigned_member_ids.length, icon: <Users size={15} />, note: tp("kPeopleNote") },
            ]}
          />
          <section className="a-card" aria-labelledby="h-track">
            <div className="a-card-head">
              <h2 id="h-track">{tu("planTitle")}</h2>
            </div>
            <StepTrack
              steps={result.data.steps.slice(0, 8).map((s, i) => ({
                id: s.skill_id,
                label: s.skill_label || s.skill_id,
                state: i === 0 ? "current" : "todo",
              }))}
            />
          </section>
          <PathwaySteps steps={result.data.steps} memberNames={names} />
        </>
      )}
    </div>
  );
}
