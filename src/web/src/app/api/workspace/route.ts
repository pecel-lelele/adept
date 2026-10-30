import { NextResponse } from "next/server";

import { call, createApiClient } from "@/lib/api/client";
import { publicOrigin } from "@/lib/api/proxy-config";
import { getSessionToken } from "@/lib/auth/session";
import { isOrgId, ORG_COOKIE, PERSONAL } from "@/lib/auth/workspace";
import { safeReturn } from "@/lib/navigation";

/** Workspace changes require an exact-origin POST and a current server-side membership. */
export function GET() {
  return new NextResponse(null, { status: 405, headers: { Allow: "POST" } });
}

export async function POST(request: Request) {
  const base = publicOrigin(request);
  if (!base || request.headers.get("origin") !== base) return new NextResponse(null, { status: 403 });
  const form = await request.formData().catch(() => undefined);
  const to = form?.get("to");
  const rawNext = form?.get("next");
  const next = typeof rawNext === "string" ? safeReturn(rawNext, "organisation") : "";
  const token = await getSessionToken();
  const go = (path: string) => NextResponse.redirect(new URL(path, base), 303);
  if (!token) return go(`/auth/login?${new URLSearchParams({ next: next || "/app" })}`);
  if (to === PERSONAL) {
    const response = go(next === "/app" || next.startsWith("/app/") ? next : "/app");
    response.cookies.delete(ORG_COOKIE);
    return response;
  }
  // Failures are browser navigations (also auto-submitted by layouts): redirect, never a blank page.
  const failed = () => go("/app?workspace_error=1");
  if (typeof to !== "string" || !isOrgId(to)) return failed();
  const api = createApiClient({ "X-Demo-User": token });
  const result = await call(api.GET("/api/v1/org/workspaces"));
  if (!result.ok) {
    return result.status === 401 ? go(`/auth/login?${new URLSearchParams({ next: next || "/app" })}`) : failed();
  }
  const space = result.data.workspaces.find((w) => w.kind === "org" && w.id === to);
  if (!space) return failed();
  const home = space.role === "member" ? "/work" : "/org";
  const response = go(next === home || next.startsWith(home + "/") ? next : home);
  response.cookies.set(ORG_COOKIE, space.id, {
    path: "/", httpOnly: true, sameSite: "lax",
    secure: process.env.NODE_ENV === "production", maxAge: 365 * 24 * 3600,
  });
  return response;
}
