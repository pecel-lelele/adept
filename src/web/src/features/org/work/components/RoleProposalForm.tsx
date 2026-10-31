import { getTranslations } from "next-intl/server";

import type { ActionState } from "@/features/pathway/action-state";
import { ActionForm } from "@/features/pathway/components/ActionForm";

/** Catalogue choices only; submitting asks HR to review, without changing the assignment. */
export async function RoleProposalForm({ action, fields, roleId, roles }: {
  action: (state: ActionState, form: FormData) => Promise<ActionState>;
  fields: Record<string, string>;
  roleId: string;
  roles: Record<string, string>;
}) {
  const t = await getTranslations("org.work");
  return (
    <details className="a-disclosure">
      <summary>{t("proposeRole")}</summary>
      <p className="a-small a-muted">{t("proposalHint")}</p>
      <ActionForm action={action} fields={fields} label={t("sendChange")} variant="outline" className="a-form-stack">
        <label className="a-field">
          <span>{t("alternativeRole")}</span>
          <select name="proposed_role_id" defaultValue="" required className="a-input">
            <option value="" disabled>{t("selectRole")}</option>
            {Object.entries(roles).filter(([id]) => id !== roleId).map(([id, label]) => (
              <option key={id} value={id}>{label}</option>
            ))}
          </select>
        </label>
      </ActionForm>
    </details>
  );
}
