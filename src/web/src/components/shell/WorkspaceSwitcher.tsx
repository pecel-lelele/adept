import { Building2, Check, ChevronsUpDown, Plus, User } from "lucide-react";
import { getTranslations } from "next-intl/server";

import type { WorkspaceOption } from "@/lib/auth/workspaces";

/**
 * Switch between the personal workspace and each organisation (one account). A plain link per
 * workspace: the server checks the membership and reloads, so nothing from the previous
 * workspace stays on screen.
 */
export async function WorkspaceSwitcher({
  workspaces,
  current,
  presentation = "dropdown",
}: {
  workspaces: WorkspaceOption[];
  current: string;
  presentation?: "dropdown" | "list";
}) {
  const t = await getTranslations("ui.workspace");
  const active = workspaces.find((w) => w.id === current) ?? workspaces[0];
  if (workspaces.length < 2 || !active) return null;
  const name = (w: WorkspaceOption) => (w.kind === "personal" ? t("personal") : w.name);
  const role = (w: WorkspaceOption) =>
    w.kind === "personal" ? t("personalHint") : w.role === "member" ? t("member") : t("manager");
  const choices = (
      <ul>
        {workspaces.map((w) => (
          <li key={w.id}>
            <a href={`/api/workspace?to=${encodeURIComponent(w.id)}`} aria-current={w.id === active.id || undefined}>
              <span className="a-wsswitch-icon" aria-hidden>
                {w.kind === "personal" ? <User size={14} /> : <Building2 size={14} />}
              </span>
              <span className="a-wsswitch-text">
                <strong>{name(w)}</strong>
                <small>{role(w)}</small>
              </span>
              {w.id === active.id ? <Check size={14} aria-hidden /> : null}
            </a>
          </li>
        ))}
        <li>
          <a href="/app/join" className="a-wsswitch-join">
            <Plus size={14} aria-hidden /> {t("join")}
          </a>
        </li>
      </ul>
  );
  if (presentation === "list") {
    return <section className="a-wslist" aria-label={t("switch")}><h2>{t("switch")}</h2>{choices}</section>;
  }
  return (
    <details className="a-wsswitch">
      <summary aria-label={t("switch")}>
        <span className="a-wsswitch-icon" aria-hidden>
          {active.kind === "personal" ? <User size={15} /> : <Building2 size={15} />}
        </span>
        <span className="a-wsswitch-text">
          <strong>{name(active)}</strong>
          <small>{role(active)}</small>
        </span>
        <ChevronsUpDown size={14} aria-hidden />
      </summary>
      {choices}
    </details>
  );
}
