"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";

import { Button } from "@/components/ui/button";

import type { ActionState } from "../action-state";

type Props = {
  action: (state: ActionState, form: FormData) => Promise<ActionState>;
  fields?: Record<string, string>;
  label: string;
  variant?: "default" | "outline";
  className?: string;
  children?: React.ReactNode;
};

/** A one-button form for a pathway server action that shows the API's error if it fails. */
export function ActionForm({ action, fields = {}, label, variant, className, children }: Props) {
  const t = useTranslations("pathway");
  const [state, formAction, pending] = useActionState(action, {});
  return (
    <form action={formAction} className={className}>
      {Object.entries(fields).map(([name, value]) => (
        <input key={name} type="hidden" name={name} value={value} />
      ))}
      <Button size="sm" variant={variant} disabled={pending} aria-busy={pending}>
        {pending ? t("saving") : label}
      </Button>
      {children}
      <span aria-live="polite" className="basis-full text-xs">
        {state.error ? (
          <span role="alert" className="text-red-700">
            {t("actionFailed", { message: state.error })}
          </span>
        ) : state.done && !pending ? (
          <span className="text-emerald-700">{t("saved")}</span>
        ) : null}
      </span>
    </form>
  );
}
