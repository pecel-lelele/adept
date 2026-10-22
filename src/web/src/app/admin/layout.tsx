import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { adminWorkspace } from "@/config/navigation";
import { getAccount } from "@/lib/auth/account";

/** Internal data pages; not linked from the landing page. */
export default async function Layout({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect("/auth/login?next=/admin");
  return (
    <Shell ws={adminWorkspace} account={account}>
      {children}
    </Shell>
  );
}
