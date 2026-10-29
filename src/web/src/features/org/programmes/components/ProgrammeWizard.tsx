"use client";

import { ArrowLeft, ArrowRight, Check, CircleAlert, Send, Users } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMemo, useState, useTransition } from "react";

import { errorMessage } from "@/lib/api/error-message";

import { Kpis } from "@/components/Kpis";
import { MetaBar } from "@/components/MetaBar";

import { generateProgrammeAction, sendProgrammeAction } from "../actions";
import type { ProgrammeBrief, ProgrammeOptions, ProgrammePlan } from "../api";

type Objective = ProgrammeBrief["objectives"][number];
type Format = NonNullable<ProgrammeBrief["formats"]>[number];
const FORMATS: Format[] = ["self_paced", "live_online", "in_person", "hybrid"];
const STEPS = ["objective", "roles", "people", "constraints"] as const;
/** Describe the work without claiming per-stage progress the API does not report. */
const STAGES = ["stageMatch", "stageRoutes", "stageBudget", "stageTimeline"] as const;

function money(n: number): string {
  return `RM ${Math.round(n).toLocaleString("en-MY")}`;
}

/**
 * HR builds an employer programme outcome-first: business objective → roles and headcount →
 * people (only members who share their skills) → date, paid learning time, budgets and course
 * restrictions. Adept then proposes one route per person from the catalogue; HR reviews and
 * sends it. Nothing is enrolled, bought or approved here.
 */
export function ProgrammeWizard({ options, orgId }: { options: ProgrammeOptions; orgId?: string }) {
  const t = useTranslations("org.programmes");
  const te = useTranslations("ui.apiErrors");
  const [step, setStep] = useState(0);
  const [title, setTitle] = useState("");
  const [objectives, setObjectives] = useState<Objective[]>([]);
  const [heads, setHeads] = useState<Record<string, number>>({});
  const [members, setMembers] = useState<string[]>(() => options.members.map((m) => m.user_id));
  const [targetDate, setTargetDate] = useState(options.default_target_date);
  const [hours, setHours] = useState(4);
  const [total, setTotal] = useState(10000);
  const [perMember, setPerMember] = useState(1500);
  const [mandatory, setMandatory] = useState(false);
  const [certificate, setCertificate] = useState(false);
  const [hrdOnly, setHrdOnly] = useState(false);
  const [formats, setFormats] = useState<Format[]>(FORMATS);
  const [plan, setPlan] = useState<ProgrammePlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [sent, setSent] = useState(false);
  const [pending, start] = useTransition();

  const roleById = useMemo(() => new Map(options.roles.map((r) => [r.role_id, r])), [options.roles]);
  const suggested = useMemo(() => {
    const ids = objectives.flatMap((o) => options.objectives.find((x) => x.id === o)?.role_ids ?? []);
    return [...new Set(ids)].filter((id) => roleById.has(id));
  }, [objectives, options.objectives, roleById]);
  const chosenRoles = Object.entries(heads).filter(([, n]) => n > 0);

  const brief: ProgrammeBrief = {
    title: title.trim() || t("defaultTitle"),
    objectives,
    roles: chosenRoles.map(([role_id, headcount]) => ({ role_id, headcount })),
    member_ids: members,
    target_date: targetDate,
    hours_per_week: hours,
    budget_total_myr: total,
    budget_per_member_myr: perMember,
    mandatory,
    certificate_required: certificate,
    hrd_claimable_only: hrdOnly,
    formats,
    scenario: "moderate",
  };

  const canNext = [
    objectives.length > 0,
    chosenRoles.length > 0 && chosenRoles.length <= 5,
    members.length > 0 && members.length <= 50,
    targetDate > new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kuala_Lumpur" }) && formats.length > 0 && hours >= 1 && total <= 5000000 && perMember <= 100000,
  ][step];

  function toggle<T>(list: T[], value: T): T[] {
    return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
  }

  function generate() {
    setError(null);
    setPlan(null);
    setGenerating(true);
    start(async () => {
      try {
        const result = await generateProgrammeAction(brief, orgId);
        if (result.error !== undefined) setError(errorMessage(te, result.error));
        else setPlan(result.plan);
      } catch {
        setError(t("generationFailed"));
      } finally {
        setGenerating(false);
      }
    });
  }

  function send() {
    if (!plan) return;
    setError(null);
    start(async () => {
      try {
        const result = await sendProgrammeAction(brief, plan.token, orgId);
        if (result.sent) setSent(true);
        else setError(result.stale ? t("stale") : errorMessage(te, result.error));
      } catch {
        setError(t("sendFailed"));
      }
    });
  }

  if (sent) {
    return (
      <section className="a-card a-gen-done" aria-live="polite">
        <span className="a-join-icon is-done" aria-hidden>
          <Check size={22} />
        </span>
        <h2>{t("sentTitle", { count: plan?.routes.length ?? 0 })}</h2>
        <p className="a-muted">{t("sentBody")}</p>
        <Link className="a-btn" href="/org/programmes">
          {t("toList")} <ArrowRight size={16} aria-hidden />
        </Link>
      </section>
    );
  }

  if (generating) {
    return (
      <section className="a-card a-gen" aria-live="polite" aria-busy="true">
        <div className="a-gen-blueprint" aria-hidden>
          {[0, 1, 2].map((row) => <div key={row}><span /><i /><span /><i /><span /></div>)}
        </div>
        <h2>{t("generating")}</h2>
        <ol className="a-gen-stages">
          {STAGES.map((key, i) => (
            <li key={key}>
              <span aria-hidden>{String(i + 1).padStart(2, "0")}</span>
              {t(key, { people: members.length, roles: chosenRoles.length })}
            </li>
          ))}
        </ol>
        <p className="a-small a-muted">{t("generatingNote")}</p>
      </section>
    );
  }

  if (plan) {
    const shortfall = plan.allocations.reduce((n, a) => n + a.shortfall, 0);
    return (
      <div className="a-stack">
        <Kpis
          items={[
            { label: t("kPeople"), value: plan.routes.length, icon: <Users size={15} /> },
            {
              label: t("kOnTrack"),
              value: plan.members_on_track,
              unit: `/ ${plan.routes.length}`,
              tone: plan.members_on_track === plan.routes.length ? "up" : "warn",
              note: t("kOnTrackNote"),
            },
            {
              label: t("kCost"),
              value: money(plan.total_cost_myr),
              tone: plan.within_programme_budget ? "up" : "down",
              note: t("ofBudget", { budget: money(brief.budget_total_myr) }),
            },
            { label: t("kShortfall"), value: shortfall, tone: shortfall ? "warn" : "up", note: t("kShortfallNote") },
          ]}
        />

        <section className="a-card">
          <div className="a-card-head">
            <h2>{t("routesTitle")}</h2>
          </div>
          <div className="a-table-wrap">
            <table className="a-table a-programme-table">
              <thead>
                <tr>
                  <th>{t("colPerson")}</th>
                  <th>{t("colRole")}</th>
                  <th>{t("colRoute")}</th>
                  <th>{t("colTime")}</th>
                  <th>{t("colCost")}</th>
                  <th>{t("colGaps")}</th>
                </tr>
              </thead>
              <tbody>
                {plan.routes.map((r) => (
                  <tr key={r.user_id}>
                    <td data-label={t("colPerson")}>{r.display_name}</td>
                    <td data-label={t("colRole")}>{r.role_label}</td>
                    <td data-label={t("colRoute")}>
                      <span className="a-route-label" data-route={r.route}>
                        {t(`route.${r.route}`)}
                      </span>
                      <span className="a-meter is-inline" aria-label={t("readiness", { share: Math.round(r.readiness * 100) })}>
                        <i style={{ width: `${Math.round(r.readiness * 100)}%` }} />
                      </span>
                    </td>
                    <td data-label={t("colTime")} data-tone={r.on_track ? "up" : "warn"}>
                      {t("weeks", { needed: r.weeks_needed, available: r.weeks_available })}
                      {!r.on_track ? <small>{t("needsHours", { hours: r.hours_per_week_needed })}</small> : null}
                    </td>
                    <td data-label={t("colCost")}>
                      {money(r.cost_myr)} <small className="a-muted">/ {money(r.budget_myr)}</small>
                    </td>
                    <td data-label={t("colGaps")}>{r.open_gaps}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {plan.unassigned_member_ids?.length ? (
            <p className="a-small a-muted">{t("unassigned", { count: plan.unassigned_member_ids?.length ?? 0 })}</p>
          ) : null}
        </section>

        <section className="a-card is-sage">
          <div className="a-card-head">
            <h2>{t("howDecided")}</h2>
          </div>
          <ul className="a-ticklist">
            {(plan.notes ?? []).map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
          <p className="a-small a-muted">{t("estimateNote", { date: plan.meta.snapshot_date })}</p>
          <MetaBar meta={plan.meta} />
        </section>

        {error ? (
          <p className="a-notice" data-tone="error" role="alert">
            <CircleAlert size={15} aria-hidden /> {error}
          </p>
        ) : null}
        <div className="a-wizard-nav">
          <button type="button" className="a-btn is-ghost" onClick={() => setPlan(null)} disabled={pending}>
            <ArrowLeft size={15} aria-hidden /> {t("editBrief")}
          </button>
          <button type="button" className="a-btn" onClick={send} disabled={pending || !plan.routes.length}>
            <Send size={15} aria-hidden /> {t("send", { count: plan.routes.length })}
          </button>
        </div>
        <p className="a-small a-muted">{t("sendNote")}</p>
      </div>
    );
  }

  return (
    <section className="a-card a-wizard">
      <ol className="a-wizard-steps" aria-label={t("stepsLabel")}>
        {STEPS.map((key, i) => (
          <li key={key} data-state={i < step ? "done" : i === step ? "current" : "todo"}>
            <button type="button" onClick={() => i < step && setStep(i)} disabled={i > step} aria-current={i === step ? "step" : undefined}>
              <span aria-hidden>{i < step ? <Check size={12} /> : i + 1}</span>
              {t(`step.${key}`)}
            </button>
          </li>
        ))}
      </ol>

      {step === 0 ? (
        <div className="a-stack">
          <label className="a-field">
            {t("titleLabel")}
            <input className="a-input" value={title} maxLength={120} placeholder={t("titlePlaceholder")} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <fieldset className="a-fieldset">
            <legend>{t("objectivesLabel")}</legend>
            <div className="a-choicegrid">
              {options.objectives.map((o) => (
                <label key={o.id} className="a-choice" data-on={objectives.includes(o.id)}>
                  <input
                    type="checkbox"
                    checked={objectives.includes(o.id)}
                    disabled={!objectives.includes(o.id) && objectives.length >= 4}
                    onChange={() => setObjectives((list) => toggle(list, o.id))}
                  />
                  <strong>{t(`objective.${o.id}`)}</strong>
                  <small>{t("rolesCount", { count: o.role_ids.length })}</small>
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      ) : null}

      {step === 1 ? (
        <div className="a-stack">
          <p className="a-small a-muted">{t("rolesHint")}</p>
          <ul className="a-rolepick-list">
            {(suggested.length ? suggested : options.roles.map((r) => r.role_id)).map((id) => {
              const r = roleById.get(id);
              if (!r) return null;
              const n = heads[id] ?? 0;
              return (
                <li key={id} data-on={n > 0}>
                  <label className="a-check">
                    <input
                      type="checkbox"
                      checked={n > 0}
                      disabled={n === 0 && chosenRoles.length >= 5}
                      onChange={() => setHeads((h) => ({ ...h, [id]: n > 0 ? 0 : 1 }))}
                    />
                    <span>
                      <strong>{r.label}</strong>
                      <small>
                        {t("readinessLine", { share: Math.round(r.team_readiness * 100), ready: r.ready_members })}
                      </small>
                      <small className="a-muted">{r.skill_labels.slice(0, 5).join(" · ")}</small>
                    </span>
                  </label>
                  {n > 0 ? (
                    <label className="a-field is-inline">
                      {t("headcount")}
                      <input
                        className="a-input"
                        type="number"
                        min={1}
                        max={50}
                        value={n}
                        onChange={(e) => setHeads((h) => ({ ...h, [id]: Math.max(1, Math.min(50, Number(e.target.value) || 1)) }))}
                      />
                    </label>
                  ) : null}
                </li>
              );
            })}
          </ul>
          <MetaBar meta={options.meta} />
        </div>
      ) : null}

      {step === 2 ? (
        <div className="a-stack">
          <p className="a-small a-muted">
            <Users size={14} aria-hidden /> {t("peopleHint")}
          </p>
          {options.members.length ? (
            <>
              <label className="a-check">
                <input
                  type="checkbox"
                  checked={members.length === options.members.length}
                  onChange={() => setMembers(members.length === options.members.length ? [] : options.members.map((m) => m.user_id))}
                />
                <span>{t("everyone", { count: options.members.length })}</span>
              </label>
              <div className="a-choicegrid is-compact">
                {options.members.map((m) => (
                  <label key={m.user_id} className="a-choice" data-on={members.includes(m.user_id)}>
                    <input type="checkbox" checked={members.includes(m.user_id)} onChange={() => setMembers((list) => toggle(list, m.user_id))} />
                    <strong>{m.display_name}</strong>
                  </label>
                ))}
              </div>
            </>
          ) : (
            <p className="a-notice">{t("noMembers")}</p>
          )}
        </div>
      ) : null}

      {step === 3 ? (
        <div className="a-stack">
          <div className="a-grid-2">
            <label className="a-field">
              {t("dateLabel")}
              <input className="a-input" type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
            </label>
            <label className="a-field">
              {t("hoursLabel")}
              <input className="a-input" type="number" min={1} max={20} value={hours} onChange={(e) => setHours(Math.max(1, Math.min(20, Number(e.target.value) || 1)))} />
              <small>{t("hoursHint")}</small>
            </label>
            <label className="a-field">
              {t("totalLabel")}
              <input className="a-input" type="number" min={0} step={100} value={total} onChange={(e) => setTotal(Math.max(0, Number(e.target.value) || 0))} />
            </label>
            <label className="a-field">
              {t("perMemberLabel")}
              <input className="a-input" type="number" min={0} step={50} value={perMember} onChange={(e) => setPerMember(Math.max(0, Number(e.target.value) || 0))} />
              <small>{t("budgetHint")}</small>
            </label>
          </div>
          <fieldset className="a-fieldset">
            <legend>{t("formatsLabel")}</legend>
            <div className="a-format-options">
              {FORMATS.map((f) => (
                <label key={f} className="a-format-option" data-on={formats.includes(f)}>
                  <input type="checkbox" checked={formats.includes(f)} onChange={() => setFormats((list) => toggle(list, f))} />
                  {t(`format.${f}`)}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="a-check">
            <input type="checkbox" checked={mandatory} onChange={() => setMandatory((v) => !v)} />
            <span>
              <strong>{t("mandatory")}</strong>
              <small>{t("mandatoryHint")}</small>
            </span>
          </label>
          <label className="a-check">
            <input type="checkbox" checked={certificate} onChange={() => setCertificate((v) => !v)} />
            <span>
              <strong>{t("certificate")}</strong>
              <small>{t("certificateHint")}</small>
            </span>
          </label>
          <label className="a-check">
            <input type="checkbox" checked={hrdOnly} onChange={() => setHrdOnly((v) => !v)} />
            <span>
              <strong>{t("hrdOnly")}</strong>
              <small>{t("hrdOnlyHint")}</small>
            </span>
          </label>
        </div>
      ) : null}

      {error ? (
        <p className="a-notice" data-tone="error" role="alert">
          <CircleAlert size={15} aria-hidden /> {error}
        </p>
      ) : null}
      <div className="a-wizard-nav">
        {step > 0 ? (
          <button type="button" className="a-btn is-ghost" onClick={() => setStep((s) => s - 1)}>
            <ArrowLeft size={15} aria-hidden /> {t("back")}
          </button>
        ) : (
          <span />
        )}
        {step < STEPS.length - 1 ? (
          <button type="button" className="a-btn" disabled={!canNext} onClick={() => setStep((s) => s + 1)}>
            {t("next")} <ArrowRight size={15} aria-hidden />
          </button>
        ) : (
          <button type="button" className="a-btn" disabled={!canNext || pending} onClick={generate}>
            {t("generate")} <ArrowRight size={15} aria-hidden />
          </button>
        )}
      </div>
    </section>
  );
}
