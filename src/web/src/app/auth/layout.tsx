import { redirect } from "next/navigation";
import { headers } from "next/headers";
import { Suspense, type ReactNode } from "react";

import { getAccount } from "@/lib/auth/account";

/** Signed-in people skip the sign-in screens (except /auth/join). */
export default async function Layout({ children }: { children: ReactNode }) {
  const path = (await headers()).get("x-adept-path") ?? "";
  const account = path.startsWith("/auth/join") ? null : await getAccount();
  if (account) redirect(account.kind === "org_admin" ? "/org" : account.has_profile ? "/app" : "/app/onboarding");
  return <Suspense fallback={<main className="a-page" />}>{children}</Suspense>;
}
