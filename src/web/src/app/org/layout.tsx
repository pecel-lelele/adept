import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { orgWorkspace } from "@/config/navigation";
import { fetchMyOrg } from "@/features/org/api";
import { getAccount } from "@/lib/auth/account";

/** Organisation workspace (/org): managers and career advisors only. */
export default async function Layout({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect("/auth/login?next=/org");
  if (account.kind !== "org_admin") redirect("/app");
  const org = await fetchMyOrg();
  return (
    <Shell ws={orgWorkspace} account={account} orgName={org.ok ? org.data.name : undefined}>
      {children}
    </Shell>
  );
}
