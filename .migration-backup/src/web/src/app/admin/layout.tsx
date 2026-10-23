import { notFound, redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { adminWorkspace } from "@/config/navigation";
import { getAccount, type Account } from "@/lib/auth/account";

/**
 * Who may open the internal data pages. ADMIN_EMAILS (comma-separated) lists them; when it is
 * unset, any signed-in account may in development and nobody may in production.
 */
function isAdmin(account: Account): boolean {
  const allowed = (process.env.ADMIN_EMAILS ?? "")
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean);
  if (allowed.length === 0) return process.env.NODE_ENV !== "production";
  return Boolean(account.email && allowed.includes(account.email.toLowerCase()));
}

/** Internal data pages; not linked from the landing page. */
export default async function Layout({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect("/auth/login?next=/admin");
  if (!isAdmin(account)) notFound();
  return (
    <Shell ws={adminWorkspace} account={account}>
      {children}
    </Shell>
  );
}
