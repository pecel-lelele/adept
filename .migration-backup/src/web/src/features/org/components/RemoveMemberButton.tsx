"use client";

import { UserMinus } from "lucide-react";
import { useTranslations } from "next-intl";
import { useTransition } from "react";

import { removeMemberAction } from "../actions";

export function RemoveMemberButton({ id, name, orgId }: { id: string; name: string; orgId?: string }) {
  const t = useTranslations("ui.org");
  const [pending, start] = useTransition();
  return (
    <button
      type="button"
      className="a-iconbtn"
      aria-label={`${t("remove")} ${name}`}
      title={t("remove")}
      disabled={pending}
      onClick={() => {
        if (!window.confirm(t("removeConfirm", { name }))) return;
        start(async () => {
          const result = await removeMemberAction(id, orgId);
          if (result.error) window.alert(result.error);
        });
      }}
    >
      <UserMinus size={16} aria-hidden />
    </button>
  );
}
