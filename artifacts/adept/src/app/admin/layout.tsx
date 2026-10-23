import { asyncView } from "@/lib/next-compat/async-view";
import { notFound, redirect } from "@/lib/next-compat/router";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { adminWorkspace } from "@/config/navigation";
import { getAccount, type Account } from "@/lib/auth/account";
import { getSession } from "@/lib/auth/session";

/**
 * Who may open the internal data pages. ADMIN_EMAILS (comma-separated) lists them; when it is
 * unset, any signed-in account may in development and nobody may in production.
 */
async function isAdmin(account: Account): Promise<boolean> {
  // ADMIN_EMAILS lives on the server; /api/session reports the result as is_admin.
  const session = await getSession();
  if (typeof session.is_admin === "boolean") return session.is_admin;
  return Boolean(account) && import.meta.env.DEV;
}

/** Internal data pages; not linked from the landing page. */
async function LayoutAsync({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect("/auth/login?next=/admin");
  if (!(await isAdmin(account))) notFound();
  return (
    <Shell ws={adminWorkspace} account={account}>
      {children}
    </Shell>
  );
}

export default asyncView(LayoutAsync);
