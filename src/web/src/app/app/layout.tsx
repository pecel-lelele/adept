import { redirect } from "next/navigation";
import { headers } from "next/headers";
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
  // All analytics need a saved profile. Keep the intake and profile routes reachable while
  // unfinished, but never show zero-personalisation analytics as a completed demo journey.
  const path = (await headers()).get("x-adept-path");
  if (!account.has_profile && path && !["/app/onboarding", "/app/profile", "/app/join"].some((route) => path === route || path.startsWith(`${route}/`))) {
    redirect("/app/onboarding");
  }
  // Same rule as the Home journey: a profile completes step 1; a saved plan means the learner
  // has seen the radar and chosen a role (steps 2 and 3).
  const [status, workspaces] = await Promise.all([
    account.has_profile ? fetchPlanStatus() : Promise.resolve(null),
    getWorkspaces(),
  ]);
  const doneSteps = !account.has_profile ? [] : status?.ok && status.data.saved ? [1, 2, 3] : [1];
  // Only lock on a known answer. If the check failed, the page itself reports the error.
  const roleChosen = status && !status.ok ? true : Boolean(status?.data.saved);
  return (
    <Shell ws={learnerWorkspace} account={account} doneSteps={doneSteps} roleChosen={roleChosen} workspaces={workspaces} current={PERSONAL}>
      {children}
    </Shell>
  );
}
