import { NextResponse } from "next/server";

import { call, createApiClient } from "@/lib/api/client";
import { getSessionToken } from "@/lib/auth/session";
import { isOrgId, ORG_COOKIE, PERSONAL } from "@/lib/auth/workspace";

/**
 * Switch workspace: GET /api/workspace?to=personal | <organisation id>. Checks the membership
 * with the API, remembers the organisation and opens its home: /work for members, /org for
 * managers and advisors. Switching reloads the pages, so no other workspace's data stays on
 * screen (Adi keeps one conversation per workspace and clears it on switch).
 */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const to = url.searchParams.get("to") ?? PERSONAL;
  const base = process.env.WEB_ORIGIN ?? url.origin;
  const go = (path: string) => NextResponse.redirect(new URL(path, base), 303);
  const token = await getSessionToken();
  if (!token) return go("/auth/login");
  if (to === PERSONAL || !isOrgId(to)) return go("/app");
  const api = createApiClient({ "X-Demo-User": token });
  const result = await call(api.GET("/api/v1/org/workspaces"));
  const space = result.ok ? result.data.workspaces.find((w) => w.kind === "org" && w.id === to) : undefined;
  if (!space) return go("/app");
  const response = go(space.role === "member" ? "/work" : "/org");
  response.cookies.set(ORG_COOKIE, space.id, {
    path: "/",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: 365 * 24 * 3600,
  });
  return response;
}
