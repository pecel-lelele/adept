import type { ReactNode } from "react";

import { AdminShell } from "@/components/shell/AdminShell";

export default function Layout({ children }: { children: ReactNode }) {
  return <AdminShell>{children}</AdminShell>;
}
