import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { learnerWorkspace } from "@/config/navigation";
import { fetchPlanStatus } from "@/features/pathway/api";
import { getAccount } from "@/lib/auth/account";
import { loginHref } from "@/lib/auth/return-path";
import { PERSONAL } from "@/lib/auth/workspace";
import { getWorkspaces } from "@/lib/auth/workspaces";

/**
 * Personal workspace (/app): every signed-in account has one, managers included. Plans, matches
 * and Adi conversations here are private; organisations see none of it.
 */
export default async function Layout({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect(await loginHref("/app"));
  // Same rule as the Home journey: a profile completes step 1; a saved plan means the learner
  // has seen the radar and chosen a role (steps 2 and 3).
  const [status, workspaces] = await Promise.all([
    account.has_profile ? fetchPlanStatus() : Promise.resolve(null),
    getWorkspaces(),
  ]);
  const doneSteps = !account.has_profile ? [] : status?.ok && status.data.saved ? [1, 2, 3] : [1];
  return (
    <Shell ws={learnerWorkspace} account={account} doneSteps={doneSteps} workspaces={workspaces} current={PERSONAL}>
      {children}
    </Shell>
  );
}
