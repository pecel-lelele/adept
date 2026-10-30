import { redirect } from "next/navigation";

import { pickOrg, type WorkspaceOption } from "@/lib/auth/workspaces";

/** The member's organisation for /work pages (the layout already redirected if none). */
export async function workOrg(): Promise<WorkspaceOption> {
  const { chosen, fallback, failure } = await pickOrg(["member"]);
  if (failure) throw new Error("Workspace membership lookup is unavailable");
  const org = chosen ?? fallback;
  if (!org) redirect("/app/join");
  return org;
}
