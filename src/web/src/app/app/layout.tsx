import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { learnerWorkspace } from "@/config/navigation";
import { getAccount } from "@/lib/auth/account";

/** Individual workspace (/app): signed-in learners only; managers go to /org. */
export default async function Layout({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect("/auth/login?next=/app");
  if (account.kind === "org_admin") redirect("/org");
  return (
    <Shell ws={learnerWorkspace} account={account} doneSteps={account.has_profile ? [1] : []}>
      {children}
    </Shell>
  );
}
