import type { ReactNode } from "react";

import { OrgShell } from "@/components/shell/OrgShell";

export default function Layout({ children }: { children: ReactNode }) {
  return <OrgShell>{children}</OrgShell>;
}
