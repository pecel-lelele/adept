"use client";

import { useTranslations } from "@/lib/next-compat/intl";
import { useActionState } from "react";

import { Button } from "@/components/ui/button";

import type { ActionState } from "../action-state";

type Props = {
  action: (state: ActionState, form: FormData) => Promise<ActionState>;
  fields: Record<string, string>;
};

/** HR / advisor confirms or rejects one completion, with an optional note to the learner. */
export function ReviewForm({ action, fields }: Props) {
  const t = useTranslations("pathway");
  const [state, formAction, pending] = useActionState(action, {});
  return (
    <form action={formAction} className="a-inline-form">
      {Object.entries(fields).map(([name, value]) => (
        <input key={name} type="hidden" name={name} value={value} />
      ))}
      <input
        type="text"
        name="note"
        maxLength={300}
        placeholder={t("verify.notePlaceholder")}
        aria-label={t("verify.note")}
        className="a-input is-small"
      />
      <Button size="sm" name="decision" value="confirm" disabled={pending}>
        {t("verify.confirm")}
      </Button>
      <Button size="sm" variant="outline" name="decision" value="reject" disabled={pending}>
        {t("verify.reject")}
      </Button>
      <span aria-live="polite" className="a-form-msg">
        {state.error ? (
          <span role="alert" className="a-error">
            {t("actionFailed", { message: state.error })}
          </span>
        ) : null}
      </span>
    </form>
  );
}
