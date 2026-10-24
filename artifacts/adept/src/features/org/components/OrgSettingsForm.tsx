"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";

import type { Schemas } from "@/lib/api";

import { updateOrgAction, type OrgActionState } from "../actions";

export function OrgSettingsForm({ org }: { org: Schemas["Organization"] }) {
  const t = useTranslations("ui.auth");
  const to = useTranslations("ui.org");
  const [state, action, pending] = useActionState<OrgActionState, FormData>(updateOrgAction, {});
  return (
    <form action={action} className="a-card a-stack" style={{ gap: 14 }}>
      <input type="hidden" name="org_id" value={org.id} />
      <label className="a-field">
        {t("orgName")}
        <input className="a-input" name="name" required minLength={2} maxLength={120} defaultValue={org.name} />
      </label>
      <div className="a-grid" style={{ gap: 12 }}>
        <label className="a-field a-span-4">
          {t("orgType")}
          <select className="a-select" name="type" defaultValue={org.type}>
            <option value="company">{t("company")}</option>
            <option value="institution">{t("institution")}</option>
          </select>
        </label>
        <label className="a-field a-span-5">
          {t("industry")}
          <input className="a-input" name="industry" maxLength={120} defaultValue={org.industry} />
        </label>
        <label className="a-field a-span-3">
          {t("size")}
          <input className="a-input" type="number" min={0} name="size" defaultValue={org.size} />
        </label>
      </div>
      {state.error ? (
        <p className="a-notice" data-tone="error" role="alert">
          {state.error}
        </p>
      ) : state.done ? (
        <p className="a-notice" data-tone="info" role="status">
          {to("saved")}
        </p>
      ) : null}
      <button className="a-btn" disabled={pending} style={{ justifySelf: "start" }}>
        {to("save")}
      </button>
    </form>
  );
}
