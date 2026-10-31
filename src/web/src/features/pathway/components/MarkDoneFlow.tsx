"use client";

import { useEffect, useState } from "react";
import { useActionState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/error-message";

import type { ActionState } from "../action-state";
import { triggerProgressToast } from "./ProgressToast";

type Props = {
  action: (state: ActionState, form: FormData) => Promise<ActionState>;
  fields: Record<string, string>;
};

/**
 * "Mark done" gated behind proof of completion.
 * Clicking the button reveals a URL input. On submission a toast fires (managed by ProgressToast)
 * and the course moves to the completed state via server revalidation.
 */
export function MarkDoneFlow({ action, fields }: Props) {
  const t = useTranslations("pathway");
  const te = useTranslations("ui.apiErrors");
  const [showForm, setShowForm] = useState(false);

  const [state, formAction, pending] = useActionState(async (prev: ActionState, formData: FormData) => {
    const res = await action(prev, formData);
    if (res.done) {
      triggerProgressToast(t("evidence.sent"));
    }
    return res;
  }, {});

  useEffect(() => {
    if (state.done && !pending) {
      setShowForm(false);
    }
  }, [state.done, pending]);

  if (state.done && !showForm) {
    return (
      <span aria-live="polite" className="a-form-msg">
        <span className="a-ok">{t("evidence.sent")}</span>
      </span>
    );
  }

  if (!showForm) {
    return (
      <button
        type="button"
        className="a-btn is-default is-small"
        onClick={() => setShowForm(true)}
      >
        {t("progress.markDone")}
      </button>
    );
  }

  return (
    <div className="a-mark-done-flow">
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
          autoFocus
        />
        <Button size="sm" disabled={pending}>
          {pending ? t("saving") : t("evidence.addProof")}
        </Button>
        <button
          type="button"
          className="a-btn is-ghost is-small"
          onClick={() => setShowForm(false)}
        >
          ✕
        </button>
        <span aria-live="polite" className="a-form-msg">
          {state.error ? (
            <span role="alert" className="a-error">
              {t("actionFailed", { message: errorMessage(te, state.error) })}
            </span>
          ) : null}
        </span>
      </form>
    </div>
  );
}
