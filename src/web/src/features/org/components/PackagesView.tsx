import Form from "next/form";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ApiError, MetaBar, PageHeader } from "@/components";
import { CertificationsCard, RoleOpeningsCard } from "@/features/jobs";
import { ActionForm } from "@/features/pathway/components/ActionForm";
import { currentWorkspace } from "@/lib/auth/workspace";
import { call, getApi, type ScenarioId } from "@/lib/api";
import { fetchGaps, fetchMembers } from "../api";
import { selectPackageAction } from "../funding-actions";

export async function PackagesView({ scenario, roleId, memberIds }: {
  scenario: ScenarioId; roleId?: string; memberIds?: string[];
}) {
  const t = await getTranslations("org.packages");
  const workspace = await currentWorkspace();
  const api = await getApi(workspace ? { workspace } : undefined);
  const [members, gaps, result] = await Promise.all([
    fetchMembers(), fetchGaps(scenario),
    call(api.GET("/api/v1/org/packages", { params: { query: {
      role_id: roleId, member_ids: memberIds, scenario,
    } } })),
  ]);
  const people = members.ok ? members.data.members.filter(m => m.intake_status === "complete") : [];
  const names = Object.fromEntries(people.map(m => [m.id, m.display_name]));
  const selected = memberIds ?? people.map(m => m.id);
  const chosenRole = roleId ?? (result.ok ? result.data.packages[0]?.role_id : undefined);
  return <div className="a-view">
    <PageHeader title={t("title")} description={t("description")} />
    <p className="a-notice">{t("policy")}</p>
    <Link className="a-link" href="/org/funding">{t("budgets")}</Link>
    <Form action="/org/plan" className="a-card">
      <input type="hidden" name="scenario" value={scenario} />
      <label className="a-field">{t("role")}<select className="a-select" name="role" defaultValue={roleId ?? (result.ok ? result.data.packages[0]?.role_id : "")}>
        {gaps.ok ? gaps.data.role_ids.map(id => <option key={id} value={id}>{gaps.data.role_labels?.[id] ?? id}</option>) : null}
      </select></label>
      <fieldset><legend>{t("cohort")}</legend>{people.map(m => <label className="a-check" key={m.id}>
        <input type="checkbox" name="member" value={m.id} defaultChecked={selected.includes(m.id)} />{m.display_name}
      </label>)}</fieldset>
      <input type="hidden" name="cohort" value="selected" />
      <button className="a-btn" type="submit">{t("compare")}</button>
    </Form>
    {!result.ok ? <ApiError message={result.message} /> : <div className="a-coursegrid">{result.data.packages.map(p => <section className="a-card" key={p.kind}>
      <h2>{t(`kind.${p.kind}`)}</h2>
      <h3>{p.role_label}</h3>
      <p>{t("summary", { cost: p.total_cost_myr.toLocaleString("en-MY"), weeks: p.max_weeks, gaps: p.unmet_skills })}</p>
      <p>{t(p.within_member_budgets ? "withinBudget" : "overBudget")}</p>
      <MetaBar meta={p.meta} />
      {p.members.map(m => <details className="a-disclosure" key={m.user_id}>
        <summary>{names[m.user_id] ?? m.user_id} · RM {m.pathway.total_cost_myr.toLocaleString("en-MY")} · {t("weeks", { count: m.pathway.total_weeks })}</summary>
        <p>{t("memberTime", { hours: m.pathway.total_hours, weekly: m.pathway.hours_per_week, available: m.available_budget_myr })}</p>
        <ol>{m.pathway.steps.map(s => <li key={s.order}>
          <strong>{s.skill_label}</strong><ul>{s.courses.map(c => <li key={c.id}><a href={c.url} target="_blank" rel="noreferrer">{c.title}</a> · RM {c.cost_myr} · {c.hours} h</li>)}</ul>
        </li>)}</ol>
        {(m.pathway.unmet ?? []).length ? <><h4>{t("unmet")}</h4><ul>{(m.pathway.unmet ?? []).map(u => <li key={u.skill_id}>{u.label}: {u.detail}</li>)}</ul></> : null}
        {(m.pathway.warnings ?? []).map((w, i) => <p className="a-small a-muted" key={i}>{w}</p>)}
      </details>)}
      <ActionForm action={selectPackageAction} label={t("select")} fields={{ role_id: p.role_id, kind: p.kind, token: p.token, scenario, ...(workspace ? { org_id: workspace } : {}) }}>
        {p.members.map(m => <input key={m.user_id} type="hidden" name="member_id" value={m.user_id} />)}
      </ActionForm>
    </section>)}</div>}
    {chosenRole ? <div className="a-split">
      <CertificationsCard roleId={chosenRole} scenario={scenario} payer="employer" max={3} />
      <RoleOpeningsCard roleId={chosenRole} scenario={scenario} variant="team" limit={4} />
    </div> : null}
  </div>;
}
