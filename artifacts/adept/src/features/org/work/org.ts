import { redirect } from "next/navigation";

import { pickOrg, type WorkspaceOption } from "@/lib/auth/workspaces";

/** The member's organisation for /work pages (the layout already redirected if none). */
export async function workOrg(): Promise<WorkspaceOption> {
  const { chosen } = await pickOrg(["member"]);
  if (!chosen) redirect("/work");
  return chosen;
}
