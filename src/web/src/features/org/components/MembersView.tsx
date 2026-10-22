import { getTranslations } from "next-intl/server";

import { ErrorState } from "@/components/ErrorState";
import { StackBar } from "@/components/viz";

import { fetchMembers, fetchMyOrg } from "../api";
import { JoinCodeCard } from "./JoinCodeCard";
import { RemoveMemberButton } from "./RemoveMemberButton";

const TONE = { complete: "up", in_progress: "warn", invited: undefined } as const;

/** Step 1 for organisations: who joined, how far their intake is, and the code to invite more. */
export async function MembersView() {
  const t = await getTranslations("ui.org");
  const tn = await getTranslations("ui.nav");
  const [org, members] = await Promise.all([fetchMyOrg(), fetchMembers()]);
  if (!members.ok) return <ErrorState failure={members} />;
  const list = members.data.members;
  const count = (s: string) => list.filter((m) => m.intake_status === s).length;
  const statusLabel = { complete: t("complete"), in_progress: t("inProgress"), invited: t("invited") };

  return (
    <div className="a-stack">
      <div className="a-pagehead">
        <h1 className="a-h1">{tn("team")}</h1>
      </div>
      <div className="a-grid">
        <section className="a-card a-span-5 a-stack">
          {org.ok && org.data.join_code ? <JoinCodeCard code={org.data.join_code} /> : null}
          <p className="a-small a-muted" style={{ margin: 0 }}>
            {t("inviteBody")}
          </p>
          <StackBar
            parts={[
              { key: "c", label: t("complete"), value: count("complete"), colour: "#2f8f5b" },
              { key: "p", label: t("inProgress"), value: count("in_progress"), colour: "#d48a26" },
              { key: "i", label: t("invited"), value: count("invited"), colour: "#c9cdc4" },
            ]}
          />
        </section>
        <section className="a-card a-span-7">
          <div className="a-card-head">
            <h2>
              {t("members")} · {list.length}
            </h2>
          </div>
          {list.length ? (
            <ul className="a-stack" style={{ gap: 8, listStyle: "none", padding: 0, margin: 0 }}>
              {list.map((m) => (
                <li key={m.id} className="a-skillrow" style={{ gridTemplateColumns: "auto minmax(0,1fr) auto auto" }}>
                  <span className="a-avatar" aria-hidden>
                    {m.display_name.slice(0, 1).toUpperCase()}
                  </span>
                  <strong>{m.display_name}</strong>
                  <span className="a-chip" data-tone={TONE[m.intake_status]}>
                    {statusLabel[m.intake_status]}
                  </span>
                  <RemoveMemberButton id={m.id} name={m.display_name} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="a-muted">{t("noMembers")}</p>
          )}
        </section>
      </div>
    </div>
  );
}
