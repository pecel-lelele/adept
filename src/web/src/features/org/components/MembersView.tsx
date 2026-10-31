import { Clock3, MailPlus, UserCheck, Users } from "lucide-react";
import { getTranslations } from "next-intl/server";
import Link from "next/link";

import { Kpis, PageHeader } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { StackBar } from "@/components/viz";

import { fetchMembers, fetchMyOrg } from "../api";
import { JoinCodeCard } from "./JoinCodeCard";
import { RemoveMemberButton } from "./RemoveMemberButton";

const TONE = { complete: "up", in_progress: "warn", invited: undefined } as const;

/** Step 1 for organisations: who joined, how far their profile is, and the code to invite more. */
export async function MembersView() {
  const t = await getTranslations("ui.org");
  const tn = await getTranslations("ui.nav");
  const tp = await getTranslations("ui.page");
  const [org, members] = await Promise.all([fetchMyOrg(), fetchMembers()]);
  if (!members.ok) return <ErrorState failure={members} />;
  const list = members.data.members;
  const count = (s: string) => list.filter((m) => m.intake_status === s).length;
  const statusLabel = { complete: t("complete"), in_progress: t("inProgress"), invited: t("invited") };

  return (
    <div className="a-view">
      <PageHeader title={tn("team")} description={tp("membersDesc")} />
      <Kpis
        items={[
          { label: t("members"), value: list.length, icon: <Users size={15} /> },
          { label: t("complete"), value: count("complete"), icon: <UserCheck size={15} />, tone: count("complete") ? "up" : undefined },
          { label: t("inProgress"), value: count("in_progress"), icon: <Clock3 size={15} />, tone: count("in_progress") ? "warn" : undefined },
          { label: t("invited"), value: count("invited"), icon: <MailPlus size={15} /> },
        ]}
      />
      <div className="a-split">
        <section className="a-card a-flush" aria-labelledby="h-members">
          <div className="a-card-head a-pad">
            <h2 id="h-members">{t("members")}</h2>
          </div>
          {list.length ? (
            <table className="a-table">
              <thead>
                <tr>
                  <th scope="col">{tp("colName")}</th>
                  <th scope="col">{tp("colProfile")}</th>
                  <th scope="col">
                    <span className="a-sr">{t("remove")}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.map((m) => (
                  <tr key={m.id}>
                    <th scope="row">
                      <span className="a-inline">
                        <span className="a-avatar" aria-hidden>
                          {m.display_name.slice(0, 1).toUpperCase()}
                        </span>
                        {m.display_name}
                      </span>
                    </th>
                    <td>
                      <span className="a-chip" data-tone={TONE[m.intake_status]}>
                        {statusLabel[m.intake_status]}
                      </span>
                    </td>
                    <td>
                      {m.intake_status === "complete" && m.skills_shared ? (
                        <Link className="a-btn is-ghost is-small" href={`/org/programmes/new?member=${encodeURIComponent(m.id)}`}>
                          {t("assignRole")}
                        </Link>
                      ) : null}
                      <RemoveMemberButton id={m.id} name={m.display_name} orgId={org.ok ? org.data.id : undefined} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="a-muted a-pad" style={{ paddingBottom: 24 }}>
              {t("noMembers")}
            </p>
          )}
        </section>
        <aside className="a-aside">
          <section className="a-card is-sage">
            {org.ok && org.data.join_code ? <JoinCodeCard code={org.data.join_code} orgId={org.data.id} /> : null}
            <p className="a-small a-muted" style={{ margin: "14px 0 0" }}>
              {t("inviteBody")}
            </p>
          </section>
          <section className="a-card" aria-labelledby="h-status">
            <div className="a-card-head">
              <h2 id="h-status">{t("intake")}</h2>
            </div>
            <StackBar
              parts={[
                { key: "c", label: t("complete"), value: count("complete"), colour: "var(--a-up)" },
                { key: "p", label: t("inProgress"), value: count("in_progress"), colour: "var(--a-warn)" },
                { key: "i", label: t("invited"), value: count("invited"), colour: "#c9cdc4" },
              ]}
            />
          </section>
        </aside>
      </div>
    </div>
  );
}
