import Link from "next/link";
import Form from "next/form";
import { getTranslations } from "next-intl/server";
import { ApiError, PageHeader } from "@/components";
import { ActionForm } from "@/features/pathway/components/ActionForm";
import { call, getApi } from "@/lib/api";
import { AssignedPackageView } from "./AssignedPackageView";
import { fundingAction } from "../funding-actions";
import { currentBudgetYear } from "../funding-year";

export async function FundingView({ year = currentBudgetYear() }: { year?: number }) {
  const t = await getTranslations("org.funding");
  const api = await getApi();
  const result = await call(api.GET("/api/v1/org/funding/{year}", { params: { path: { year } } }));
  if (!result.ok) return <ApiError message={result.message} />;
  const ledger = result.data;
  const requesting = !ledger.manager && year === currentBudgetYear();
  const catalogue = requesting ? await call(api.GET("/api/v1/pathway/catalogue")) : null;
  const matches = requesting ? await call(api.GET("/api/v1/matches")) : null;
  const names = ledger.manager ? await call(api.GET("/api/v1/org/members")) : null;
  const name = (id: string) => names?.ok ? names.data.members.find(m => m.id === id)?.display_name ?? id : id;
  const amount = (value: string | number) => Number(value).toLocaleString("en-MY", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return <div className="a-view">
    <PageHeader title={t("title")} description={t("description", { year })} />
    <p className="a-notice">{t("policy")}</p>
    <Form action={ledger.manager ? "/org/funding" : "/app/funding"} className="a-rolepick">
      <label className="a-field">{t("budgetYear")}<select name="year" defaultValue={year} className="a-select">
        {(ledger.available_years ?? [year]).map(y => <option key={y} value={y}>{y}</option>)}
      </select></label>
      <button className="a-btn is-small" type="submit">{t("openYear")}</button>
    </Form>
    {year !== currentBudgetYear() ? <p className="a-notice">{t("historicalYear")}</p> : null}
    {requesting ? <AssignedPackageView /> : null}
    <p><Link className="a-link" href={ledger.manager ? "/org/plan" : "/app/progress"}>{t("back")}</Link></p>
    {ledger.budgets.map(b => <section className="a-card" key={b.user_id}>
      <h2>{name(b.user_id)}</h2>
      <p>{t("balance", { budget: amount(b.amount_myr), reserved: amount(b.reserved_myr), paid: amount(b.paid_myr), available: amount(b.available_myr) })}</p>
      {ledger.manager ? <ActionForm action={fundingAction} fields={{ op: "budget", year: String(year), user_id: b.user_id }} label={t("setBudget")}>
        <label className="a-field">{t("annualBudget")}<input className="a-input" name="amount_myr" type="number" min="0" max="1000000" step="0.01" required defaultValue={Number(b.amount_myr)} /></label>
      </ActionForm> : null}
    </section>)}
    {requesting && catalogue?.ok && matches?.ok ? <section className="a-card">
      <h2>{t("request")}</h2>
      <ActionForm action={fundingAction} fields={{ op: "request", year: String(year) }} label={t("request")}>
        <label className="a-field">{t("role")}<select className="a-select" name="role_id" required>{matches.data.matches.map(r => <option key={r.role_id} value={r.role_id}>{r.label}</option>)}</select></label>
        <label className="a-field">{t("course")}<select className="a-select" name="course_id" required>{catalogue.data.courses.filter(c => c.price_basis === "per_course" && (c.cost_myr > 0 || c.price_status === "certificate_price_unknown")).map(c => <option key={c.id} value={c.id}>{c.title} · {c.price_status === "certificate_price_unknown" ? t("quoteNeeded") : `RM ${amount(c.cost_myr)}`}</option>)}</select></label>
        <label className="a-field">{t("quote")}<input className="a-input" name="quote_url" type="url" pattern="https://.*" required maxLength={500} /></label>
        <label className="a-field">{t("amount")}<input className="a-input" name="amount_myr" type="number" min="0.01" max="1000000" step="0.01" required /></label>
      </ActionForm>
    </section> : null}
    <h2>{t("requests")}</h2>
    {ledger.claims.length === 0 ? <p>{t("empty")}</p> : null}
    {ledger.claims.map(c => {
      const fields = { year: String(c.year), claim_id: c.id, revision: String(c.revision) };
      return <section className="a-card" key={c.id}>
        <h3>{c.course.title} · {name(c.user_id)}</h3>
        <p>{t(`status.${c.status}`)} · {t("amount")}: RM {amount(c.requested_myr)} · {t("claimed")}: RM {amount(c.claimed_myr)}</p>
        <a className="a-link" href={c.quote_url} target="_blank" rel="noreferrer">{t("quote")}</a>{" "}
        {c.receipt_url ? <a className="a-link" href={c.receipt_url} target="_blank" rel="noreferrer">{t("receipt")}</a> : null}{" "}
        {c.certificate_url ? <a className="a-link" href={c.certificate_url} target="_blank" rel="noreferrer">{t("certificate")}</a> : null}
        {c.receipt_reference ? <p>{t("receiptReference")}: {c.receipt_reference}</p> : null}
        {c.payment_reference ? <p>{t("paymentReference")}: {c.payment_reference}</p> : null}
        {!ledger.manager && c.status === "approved" ? <>
        <ActionForm action={fundingAction} fields={{ ...fields, op: "completion" }} label={t("sendCertificate")}>
          <label className="a-field">{t("certificate")}<input name="certificate_url" type="url" pattern="https://.*" maxLength={500} required className="a-input" /></label>
        </ActionForm>
        <ActionForm action={fundingAction} fields={{ ...fields, op: "submit" }} label={t("submit")}>
          <p>{t("completionFirst")}</p>
          <label className="a-field">{t("amount")}<input name="amount_myr" type="number" step="0.01" min="0.01" max={Number(c.approved_myr)} required className="a-input" /></label>
          <label className="a-field">{t("receipt")}<input name="receipt_url" type="url" pattern="https://.*" maxLength={500} required className="a-input" /></label>
          <label className="a-field">{t("receiptReference")}<input name="receipt_reference" minLength={3} maxLength={120} required className="a-input" /></label>
          <label className="a-field">{t("purchased")}<input name="purchased_at" type="datetime-local" required className="a-input" /></label>
        </ActionForm></> : null}
        {ledger.manager && c.status === "requested" ? <ActionForm action={fundingAction} fields={{ ...fields, op: "approve" }} label={t("approve")} /> : null}
        {ledger.manager && c.status === "submitted" ? <ActionForm action={fundingAction} fields={{ ...fields, op: "accept_claim" }} label={t("acceptClaim")}><p>{t("checkReceipt")}</p></ActionForm> : null}
        {ledger.manager && c.status === "payable" ? <ActionForm action={fundingAction} fields={{ ...fields, op: "mark_paid" }} label={t("recordPayment")}>
          <label className="a-field">{t("paymentReference")}<input name="payment_reference" maxLength={120} required className="a-input" /></label>
        </ActionForm> : null}
        {ledger.manager && !["paid", "rejected", "cancelled"].includes(c.status) ? <ActionForm action={fundingAction} fields={{ ...fields, op: "reject" }} label={t("reject")} variant="outline">
          <label className="a-field">{t("reason")}<input name="note" required maxLength={300} className="a-input" /></label>
        </ActionForm> : null}
        {!ledger.manager && ["requested", "approved"].includes(c.status) ? <ActionForm action={fundingAction} fields={{ ...fields, op: "cancel" }} label={t("cancel")} variant="outline" /> : null}
        <details className="a-disclosure"><summary>{t("history")}</summary><ul>{(c.events ?? []).map((e, i) => <li key={i}>{e.at} · {e.action} {e.note}</li>)}</ul></details>
      </section>;
    })}
  </div>;
}
