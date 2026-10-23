import Form from "next/form";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { ApiError, PageHeader } from "@/components";
import { ActionForm } from "@/features/pathway/components/ActionForm";
import { call, getApi } from "@/lib/api";

import { budgetAction } from "../funding-actions";
import { currentBudgetYear } from "../funding-year";

/**
 * HR's yearly training budget per member. It is a planning input for comparing team packages;
 * the organisation pays for training directly, so members have no claims or reimbursements.
 */
export async function FundingView({ year = currentBudgetYear() }: { year?: number }) {
  const t = await getTranslations("org.funding");
  const api = await getApi();
  const result = await call(api.GET("/api/v1/org/funding/{year}", { params: { path: { year } } }));
  if (!result.ok) return <ApiError message={result.message} />;
  const ledger = result.data;
  if (!ledger.manager) redirect("/work/plan");
  const names = await call(api.GET("/api/v1/org/members"));
  const name = (id: string) => (names.ok ? names.data.members.find((m) => m.id === id)?.display_name ?? id : id);
  const rm = (value: string | number) => Number(value).toLocaleString("en-MY", { maximumFractionDigits: 2 });
  return (
    <div className="a-view">
      <PageHeader title={t("title")} description={t("description")}>
        <Link className="a-link" href="/org/plan">{t("back")}</Link>
      </PageHeader>
      <Form action="/org/funding" className="a-card a-controls">
        <label className="a-field">
          {t("budgetYear")}
          <select name="year" defaultValue={year} className="a-select">
            {(ledger.available_years ?? [year]).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>
        <button className="a-btn is-ghost is-small" type="submit">{t("openYear")}</button>
      </Form>
      <ul className="a-jobs">
        {ledger.budgets.map((b) => (
          <li className="a-job" key={b.user_id}>
            <div className="a-job-main">
              <strong className="a-job-title">{name(b.user_id)}</strong>
              <span className="a-job-where">{t("perYear", { amount: rm(b.amount_myr), year })}</span>
            </div>
            <ActionForm action={budgetAction} fields={{ year: String(year), user_id: b.user_id, org_id: ledger.org_id }} label={t("save")} className="a-inline-form">
              <label className="a-field">
                <span className="a-sr">{t("annualBudget")}</span>
                <input className="a-input" name="amount_myr" type="number" min="0" max="1000000" step="0.01" required defaultValue={Number(b.amount_myr)} aria-label={t("annualBudget")} />
              </label>
            </ActionForm>
          </li>
        ))}
      </ul>
    </div>
  );
}
