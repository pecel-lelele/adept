import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { learnerWorkspace } from "@/config/navigation";
import { fetchMyOrg } from "@/features/org/api";
import { fetchPlanStatus } from "@/features/pathway/api";
import { getAccount } from "@/lib/auth/account";

/** Individual workspace (/app): signed-in learners only; managers go to /org. */
export default async function Layout({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect("/auth/login?next=/app");
  if (account.kind === "org_admin") redirect("/org");
  // Same rule as the Home journey: a profile completes step 1; a saved plan means the learner
  // has seen the radar and chosen a role (steps 2 and 3).
  const [status, org] = await Promise.all([
    account.has_profile ? fetchPlanStatus() : Promise.resolve(null),
    account.org_id ? fetchMyOrg() : Promise.resolve(null),
  ]);
  const doneSteps = !account.has_profile ? [] : status?.ok && status.data.saved ? [1, 2, 3] : [1];
  return (
    <Shell ws={learnerWorkspace} account={account} doneSteps={doneSteps} orgName={org?.ok ? org.data.name : undefined}>
      {children}
    </Shell>
  );
}
