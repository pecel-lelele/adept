"use client";

import { useTranslations } from "next-intl";
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
    <form action={formAction} className="flex flex-wrap items-center gap-2">
      {Object.entries(fields).map(([name, value]) => (
        <input key={name} type="hidden" name={name} value={value} />
      ))}
      <input
        type="text"
        name="note"
        maxLength={300}
        placeholder={t("verify.notePlaceholder")}
        aria-label={t("verify.note")}
        className="w-full min-w-0 rounded-md border bg-background px-2 py-1 text-xs sm:w-auto sm:flex-1"
      />
      <Button size="sm" name="decision" value="confirm" disabled={pending}>
        {t("verify.confirm")}
      </Button>
      <Button size="sm" variant="outline" name="decision" value="reject" disabled={pending}>
        {t("verify.reject")}
      </Button>
      <span aria-live="polite" className="basis-full text-xs">
        {state.error ? (
          <span role="alert" className="text-red-700">
            {t("actionFailed", { message: state.error })}
          </span>
        ) : null}
      </span>
    </form>
  );
}
