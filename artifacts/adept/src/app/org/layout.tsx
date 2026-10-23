import { asyncView } from "@/lib/next-compat/async-view";
import { redirect } from "@/lib/next-compat/router";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { orgWorkspace } from "@/config/navigation";
import { fetchMembers } from "@/features/org/api";
import { getAccount } from "@/lib/auth/account";
import { getWorkspaces, pickOrg } from "@/lib/auth/workspaces";

/** Organisation management (/org): managers and career advisors of the chosen organisation. */
async function LayoutAsync({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect("/auth/login?next=/org");
  const { chosen, remembered, fallback } = await pickOrg(["manager", "advisor"]);
  if (!chosen) {
    if (remembered?.role === "member") redirect("/work");
    if (fallback) redirect(`/api/workspace?to=${encodeURIComponent(fallback.id)}`);
    redirect(account.kind === "org_admin" ? "/org/setup" : "/app");
  }
  const [members, workspaces] = await Promise.all([fetchMembers(), getWorkspaces()]);
  // Same rule as the dashboard's team journey: someone joined → step 1; a completed profile
  // makes the radar, gaps and programmes meaningful → steps 2-4.
  const list = members.ok ? members.data.members : [];
  const ready = list.some((m) => m.intake_status === "complete");
  const doneSteps = ready ? [1, 2, 3, 4] : list.length ? [1] : [];
  return (
    <Shell ws={orgWorkspace} account={account} orgName={chosen.name} doneSteps={doneSteps} workspaces={workspaces} current={chosen.id}>
      {children}
    </Shell>
  );
}

export default asyncView(LayoutAsync);
