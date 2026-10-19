import type { ReactNode } from "react";

import { adminNav } from "@/config/navigation";

import { Shell } from "./Shell";

/** Internal admin pages; not linked from the landing page. */
export function AdminShell({ children }: { children: ReactNode }) {
  return (
    <Shell nav={adminNav} modeLabel="Admin" showScenario={false}>
      {children}
    </Shell>
  );
}
