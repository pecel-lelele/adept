import { useTranslations } from "next-intl";

import type { Schemas } from "@/lib/api";

export function ProfileNote({ note }: { note?: Schemas["RoleMatch"]["profile_note"] }) {
  const t = useTranslations("matching");
  return note === "add_skills" ? (
    <p className="a-notice" data-tone="info" role="status">{t("addSkillsNote")}</p>
  ) : null;
}
