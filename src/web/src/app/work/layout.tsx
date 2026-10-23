import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { workWorkspace } from "@/config/navigation";
import { getAccount } from "@/lib/auth/account";
import { getWorkspaces, pickOrg } from "@/lib/auth/workspaces";

/**
 * An organisation member's workspace (/work): their own participation in its programmes. Joining
 * with a code gives this view; management needs a manager role in that organisation.
 */
export default async function Layout({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect("/auth/login?next=/work");
  const { chosen, remembered, fallback } = await pickOrg(["member"]);
  if (!chosen) {
    if (remembered && remembered.role !== "member") redirect("/org");
    if (fallback) redirect(`/api/workspace?to=${encodeURIComponent(fallback.id)}`);
    redirect("/app/join");
  }
  const workspaces = await getWorkspaces();
  return (
    <Shell ws={workWorkspace} account={account} orgName={chosen.name} workspaces={workspaces} current={chosen.id}>
      {children}
    </Shell>
  );
}
