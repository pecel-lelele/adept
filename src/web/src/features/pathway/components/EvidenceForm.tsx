"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";

import { errorMessage } from "@/lib/api/error-message";

import { Button } from "@/components/ui/button";

import type { ActionState } from "../action-state";

type Props = {
  action: (state: ActionState, form: FormData) => Promise<ActionState>;
  fields: Record<string, string>;
};

/** Learner pastes a certificate / credential link for a completed course. */
export function EvidenceForm({ action, fields }: Props) {
  const t = useTranslations("pathway");
  const te = useTranslations("ui.apiErrors");
  const [state, formAction, pending] = useActionState(action, {});
  return (
    <form action={formAction} className="a-inline-form">
      {Object.entries(fields).map(([name, value]) => (
        <input key={name} type="hidden" name={name} value={value} />
      ))}
      <input
        type="url"
        name="url"
        required
        pattern="https://.*"
        placeholder={t("evidence.urlPlaceholder")}
        aria-label={t("evidence.addProof")}
        className="a-input is-small"
      />
      <Button size="sm" variant="outline" disabled={pending}>
        {pending ? t("saving") : t("evidence.addProof")}
      </Button>
      <span aria-live="polite" className="a-form-msg">
        {state.error ? (
          <span role="alert" className="a-error">
            {t("actionFailed", { message: errorMessage(te, state.error) })}
          </span>
        ) : state.done && !pending ? (
          <span className="a-ok">{t("evidence.sent")}</span>
        ) : null}
      </span>
    </form>
  );
}
