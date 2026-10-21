import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { getAuthMode, getDemoUser } from "@/lib/auth/session";

import { AppShell } from "@/components/shell/AppShell";

export default async function Layout({ children }: { children: ReactNode }) {
  if (getAuthMode() === "demo") {
    const user = await getDemoUser();
    const org = user === "demo-company" || user === "demo-institution";
    if (!user) redirect("/auth/login?mode=individual&next=/app");
    if (org) redirect("/org");
  }
  return <AppShell>{children}</AppShell>;
}
