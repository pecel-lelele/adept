import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { orgWorkspace } from "@/config/navigation";
import { fetchMembers, fetchMyOrg } from "@/features/org/api";
import { getAccount } from "@/lib/auth/account";

/** Organisation workspace (/org): managers and career advisors only. */
export default async function Layout({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect("/auth/login?next=/org");
  if (account.kind !== "org_admin") redirect("/app");
  const [org, members] = await Promise.all([fetchMyOrg(), fetchMembers()]);
  // Same rule as the dashboard's team journey: someone joined → step 1; a completed profile
  // makes the radar, gaps and team plan meaningful → steps 2-4.
  const list = members.ok ? members.data.members : [];
  const ready = list.some((m) => m.intake_status === "complete");
  const doneSteps = ready ? [1, 2, 3, 4] : list.length ? [1] : [];
  return (
    <Shell ws={orgWorkspace} account={account} orgName={org.ok ? org.data.name : undefined} doneSteps={doneSteps}>
      {children}
    </Shell>
  );
}
