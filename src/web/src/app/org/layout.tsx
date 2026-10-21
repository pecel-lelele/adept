import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { getAuthMode, getDemoUser } from "@/lib/auth/session";

import { OrgShell } from "@/components/shell/OrgShell";

export default async function Layout({ children }: { children: ReactNode }) {
  if (getAuthMode() === "demo") {
    const user = await getDemoUser();
    const org = user === "demo-company" || user === "demo-institution";
    if (!user) redirect("/auth/login?mode=organisation&next=/org");
    if (!org) redirect("/app");
  }
  return <OrgShell>{children}</OrgShell>;
}
