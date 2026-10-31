"use client";

import { useEffect, useRef, useState } from "react";
import { useActionState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/error-message";

import type { ActionState } from "../action-state";

type Props = {
  action: (state: ActionState, form: FormData) => Promise<ActionState>;
  fields: Record<string, string>;
};

/**
 * "Mark done" gated behind proof of completion.
 * Clicking the button reveals a URL input. On submission a toast fires and
 * the course moves to the completed/pending state via server revalidation.
 */
export function MarkDoneFlow({ action, fields }: Props) {
  const t = useTranslations("pathway");
  const te = useTranslations("ui.apiErrors");
  const [showForm, setShowForm] = useState(false);
  const [toastVisible, setToastVisible] = useState(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [state, formAction, pending] = useActionState(action, {});

  // When the server action succeeds show a toast and hide the form
  useEffect(() => {
    if (state.done && !pending) {
      setToastVisible(true);
      setShowForm(false);
      if (toastTimer.current) clearTimeout(toastTimer.current);
      toastTimer.current = setTimeout(() => setToastVisible(false), 3500);
    }
    return () => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, [state.done, pending]);

  if (state.done && !showForm) {
    // Course now revalidated server-side; show inline confirmation until page re-renders
    return (
      <span aria-live="polite" className="a-form-msg">
        <span className="a-ok">{t("evidence.sent")}</span>
        {toastVisible ? (
          <div role="status" className="a-toast">
            {t("evidence.sent")}
          </div>
        ) : null}
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
      {toastVisible ? (
        <div role="status" className="a-toast">
          {t("evidence.sent")}
        </div>
      ) : null}
    </div>
  );
}

