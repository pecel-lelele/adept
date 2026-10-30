import { redirect } from "next/navigation";
import { headers } from "next/headers";
import { Suspense, type ReactNode } from "react";

import { getAccount } from "@/lib/auth/account";
import { safeReturn } from "@/lib/navigation";

/** Signed-in people skip the sign-in screens (except /auth/join). */
export default async function Layout({ children }: { children: ReactNode }) {
  const path = (await headers()).get("x-adept-path") ?? "";
  const account = path.startsWith("/auth/join") ? null : await getAccount();
  if (account) {
    const query = new URLSearchParams((await headers()).get("x-adept-search") ?? "");
    const fallback = account.kind === "org_admin" ? "/org" : account.has_profile ? "/app" : "/app/onboarding";
    redirect(query.has("next") ? safeReturn(query.get("next"), account.kind === "org_admin" ? "organisation" : "individual") : fallback);
  }
  return <Suspense fallback={<main className="a-page" />}>{children}</Suspense>;
}
