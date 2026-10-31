import { NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/auth/session";
import { ORG_COOKIE } from "@/lib/auth/workspace";
import { call, getApi } from "@/lib/api";
import { publicOrigin } from "@/lib/api/proxy-config";
import { getSafeRedirectPath } from "@/lib/auth/safeRedirect";

export function GET() {
  return new NextResponse(null, { status: 405, headers: { Allow: "POST" } });
}

/**
 * Sign out: revoke the session on the API, then always clear this browser's cookies and go to
 * a validated same-origin `next` path (default "/"). A failed revocation does not keep the
 * browser signed in; it is reported in the `x-adept-logout` header and the server log.
 */
export async function POST(request: Request) {
  const origin = publicOrigin(request);
  if (!origin || request.headers.get("origin") !== origin) return new NextResponse(null, { status: 403 });
  const result = await call((await getApi({ workspace: "personal" })).POST("/api/v1/auth/logout"));
  // 401: the session was already invalid, which is the outcome logout wants.
  const revoked = result.ok || result.status === 401;
  const destination = getSafeRedirectPath(new URL(request.url).searchParams.get("next"), origin, "/");
  const response = new NextResponse(null, { status: 303, headers: { location: destination } });
  if (!revoked) {
    console.warn(`Logout: server-side session revocation failed (${result.code || result.status}); cookies cleared.`);
    response.headers.set("x-adept-logout", "revoke-failed");
  }
  response.cookies.delete(SESSION_COOKIE);
  response.cookies.delete(ORG_COOKIE);
  return response;
}
