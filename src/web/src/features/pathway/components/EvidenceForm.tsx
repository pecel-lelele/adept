"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";

import { Button } from "@/components/ui/button";

import type { ActionState } from "../action-state";

type Props = {
  action: (state: ActionState, form: FormData) => Promise<ActionState>;
  fields: Record<string, string>;
};

/** Learner pastes a certificate / credential link for a completed course. */
export function EvidenceForm({ action, fields }: Props) {
  const t = useTranslations("pathway");
  const [state, formAction, pending] = useActionState(action, {});
  return (
    <form action={formAction} className="flex flex-wrap items-center gap-2">
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
        className="w-full min-w-0 rounded-md border bg-background px-2 py-1 text-xs sm:w-auto sm:flex-1"
      />
      <Button size="sm" variant="outline" disabled={pending}>
        {pending ? t("saving") : t("evidence.addProof")}
      </Button>
      <span aria-live="polite" className="basis-full text-xs">
        {state.error ? (
          <span role="alert" className="text-red-700">
            {t("actionFailed", { message: state.error })}
          </span>
        ) : state.done && !pending ? (
          <span className="text-emerald-700">{t("evidence.sent")}</span>
        ) : null}
      </span>
    </form>
  );
}
