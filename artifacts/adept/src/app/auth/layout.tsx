import { asyncView } from "@/lib/next-compat/async-view";
import { currentPath, redirect } from "@/lib/next-compat/router";
import { Suspense, type ReactNode } from "react";

import { getAccount } from "@/lib/auth/account";

/** Signed-in people skip the sign-in screens (except /auth/join). */
async function LayoutAsync({ children }: { children: ReactNode }) {
  const path = currentPath();
  const account = path.startsWith("/auth/join") ? null : await getAccount();
  if (account) redirect(account.kind === "org_admin" ? "/org" : account.has_profile ? "/app" : "/app/onboarding");
  return <Suspense fallback={<main className="a-page" />}>{children}</Suspense>;
}

export default asyncView(LayoutAsync);
