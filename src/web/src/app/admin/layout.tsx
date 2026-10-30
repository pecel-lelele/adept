import { notFound, redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/Shell";
import { adminWorkspace } from "@/config/navigation";
import { getAccount, type Account } from "@/lib/auth/account";
import { loginHref } from "@/lib/auth/return-path";

/**
 * Stable account IDs provisioned by the operator. Signup email is not verified identity.
 * An empty list denies access in every environment, like the API administrator guard.
 */
function isAdmin(account: Account): boolean {
  const allowed = (process.env.ADMIN_USER_IDS ?? "")
    .split(",")
    .map((id) => id.trim())
    .filter(Boolean);
  return allowed.includes(account.id);
}

/** Internal data pages; not linked from the landing page. */
export default async function Layout({ children }: { children: ReactNode }) {
  const account = await getAccount();
  if (!account) redirect(await loginHref("/admin"));
  if (!isAdmin(account)) notFound();
  return (
    <Shell ws={adminWorkspace} account={account}>
      {children}
    </Shell>
  );
}
