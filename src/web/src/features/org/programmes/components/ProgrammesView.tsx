import { ClipboardList, Plus } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { EmptyState, ErrorState, Kpis, PageHeader } from "@/components";

import { fetchMembers } from "../../api";
import { fetchProgrammes } from "../api";

/** HR's programmes: who accepted, is still deciding, asked for a change or declined. */
export async function ProgrammesView() {
  const t = await getTranslations("org.programmes");
  const tw = await getTranslations("org.work");
  const [result, members] = await Promise.all([fetchProgrammes(), fetchMembers()]);
  if (!result.ok) return <ErrorState failure={result} />;
  const names = new Map(members.ok ? members.data.members.map((m) => [m.id, m.display_name]) : []);
  const list = result.data.programmes;
  const sum = (key: "accepted" | "pending" | "declined" | "change_requested") => list.reduce((n, p) => n + p[key], 0);
  return (
    <div className="a-view">
      <PageHeader eyebrow={t("eyebrow")} title={t("listTitle")} description={t("listDesc")}>
        <Link className="a-btn" href="/org/programmes/new">
          <Plus size={15} aria-hidden /> {t("new")}
        </Link>
      </PageHeader>
      <Kpis
        items={[
          { label: t("kSent"), value: list.length, icon: <ClipboardList size={15} /> },
          { label: t("kAccepted"), value: sum("accepted"), tone: "up" },
          { label: t("kWaiting"), value: sum("pending"), tone: sum("pending") ? "warn" : undefined },
          { label: t("kChanges"), value: sum("change_requested") + sum("declined"), tone: sum("change_requested") ? "warn" : undefined, note: t("kChangesNote") },
        ]}
      />
      {list.length ? (
        list.map((p) => {
          const b = p.record.brief;
          return (
            <article key={p.record.id} className="a-card">
              <header className="a-programme-head">
                <div>
                  <h2>{b.title}</h2>
                  <p className="a-small a-muted">
                    {b.objectives.map((o) => t(`objective.${o}`)).join(" · ")} · {t("dueOn", { date: b.target_date })} ·{" "}
                    {t("hoursWeek", { hours: b.hours_per_week })} · {t("budgetOf", { budget: Math.round(b.budget_total_myr) })}
                    {b.mandatory ? ` · ${tw("required")}` : ""}
                  </p>
                </div>
                <ul className="a-programme-counts" aria-label={t("colStatus")}>
                  <li data-tone="up">{t("nAccepted", { count: p.accepted })}</li>
                  <li data-tone={p.pending ? "warn" : undefined}>{t("nWaiting", { count: p.pending })}</li>
                  {p.change_requested ? <li data-tone="warn">{t("nChanges", { count: p.change_requested })}</li> : null}
                  {p.declined ? <li data-tone="down">{t("nDeclined", { count: p.declined })}</li> : null}
                </ul>
              </header>
              <details className="a-disclosure">
                <summary>{t("people", { count: p.assignments.length })}</summary>
                <div className="a-table-wrap">
                  <table className="a-table a-programme-table">
                    <thead>
                      <tr>
                        <th>{t("colPerson")}</th>
                        <th>{t("colRole")}</th>
                        <th>{t("colRoute")}</th>
                        <th>{t("colStatus")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.assignments.map((a) => (
                        <tr key={a.user_id}>
                          <td data-label={t("colPerson")}>{names.get(a.user_id) ?? t("formerMember")}</td>
                          <td data-label={t("colRole")}>{a.agreement.role_label}</td>
                          <td data-label={t("colRoute")}>{t(`route.${a.agreement.route}`)}</td>
                          <td data-label={t("colStatus")}>
                            {tw(`status.${a.status}`)}
                            {a.change_reason ? <small> · {tw(`reason.${a.change_reason}`)}</small> : null}
                            {a.note ? <small className="a-muted"> “{a.note}”</small> : null}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </article>
          );
        })
      ) : (
        <EmptyState
          title={t("emptyTitle")}
          description={t("emptyDesc")}
          action={
            <Link className="a-btn" href="/org/programmes/new">
              <Plus size={15} aria-hidden /> {t("new")}
            </Link>
          }
        />
      )}
    </div>
  );
}
