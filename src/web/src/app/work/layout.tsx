import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { ErrorState } from "@/components/ErrorState";
import { WorkspaceActivation } from "@/components/WorkspaceActivation";
import { workWorkspace } from "@/config/navigation";
import { getAccount } from "@/lib/auth/account";
import { currentPath, loginHref } from "@/lib/auth/return-path";
import { getWorkspaces, pickOrg } from "@/lib/auth/workspaces";

/**
 * An organisation member's workspace (/work): their own participation in its programmes. Joining
 * with a code gives this view; management needs a manager role in that organisation.
 */
export default async function Layout({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect(await loginHref("/work"));
  const { chosen, remembered, fallback, failure } = await pickOrg(["member"]);
  if (failure) return <ErrorState failure={failure} />;
  if (!chosen) {
    if (fallback) return <WorkspaceActivation to={fallback.id} next={await currentPath("/work")} />;
    if (remembered && remembered.role !== "member") redirect("/org");
    redirect("/app/join");
  }
  const workspaces = await getWorkspaces();
  return (
    <Shell ws={workWorkspace} account={account} orgName={chosen.name} workspaces={workspaces} current={chosen.id}>
      {children}
    </Shell>
  );
}
