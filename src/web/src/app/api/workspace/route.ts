import { NextResponse } from "next/server";

import { call, createApiClient } from "@/lib/api/client";
import { isSameOriginRequest, publicOrigin } from "@/lib/api/proxy-config";
import { getSessionToken } from "@/lib/auth/session";
import { isOrgId, ORG_COOKIE, PERSONAL } from "@/lib/auth/workspace";

/**
 * Switch workspace: GET /api/workspace?to=personal | <organisation id>, or POST with a form
 * field `to`. Checks the membership with the API, remembers the organisation and opens its
 * home: /work for members, /org for managers and advisors. Switching reloads the pages, so no
 * other workspace's data stays on screen (Adi keeps one conversation per workspace and clears
 * it on switch).
 *
 * Setting the cookie is a state change, so it happens only for requests from Adept's own
 * pages (Fetch Metadata, Origin or Referer). A cross-site link or form opens /app instead and
 * leaves the remembered workspace unchanged.
 */
async function switchTo(request: Request, to: string): Promise<NextResponse> {
  const base = publicOrigin(request);
  if (!base) return new NextResponse(null, { status: 500 });
  const go = (path: string) => NextResponse.redirect(new URL(path, base), 303);
  const token = await getSessionToken();
  if (!token) return go("/auth/login");
  if (to === PERSONAL || !isOrgId(to) || !isSameOriginRequest(request, base)) return go("/app");
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

export async function GET(request: Request) {
  return switchTo(request, new URL(request.url).searchParams.get("to") ?? PERSONAL);
}

export async function POST(request: Request) {
  const base = publicOrigin(request);
  // Forms always send Origin; require an exact match for POST.
  if (!base || request.headers.get("origin") !== base) return new NextResponse(null, { status: 403 });
  const form = await request.formData().catch(() => undefined);
  const to = form?.get("to");
  return switchTo(request, typeof to === "string" ? to : PERSONAL);
}
