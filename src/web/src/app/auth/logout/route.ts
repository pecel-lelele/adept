import { NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/auth/session";
import { ORG_COOKIE } from "@/lib/auth/workspace";
import { call, getApi } from "@/lib/api";
import { getSafeRedirectPath } from "@/lib/auth/safeRedirect";

export function GET() {
  return new NextResponse(null, { status: 405, headers: { Allow: "POST" } });
}

export async function POST(request: Request) {
  const url = new URL(request.url);
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? url.host;
  const protocol = request.headers.get("x-forwarded-proto") ?? url.protocol.replace(":", "");
  const publicOrigin = process.env.WEB_ORIGIN ?? `${protocol}://${host}`;
  if (request.headers.get("origin") !== publicOrigin) return new NextResponse(null, { status: 403 });
  const result = await call((await getApi({ workspace: "personal" })).POST("/api/v1/auth/logout"));
  if (!result.ok && result.status !== 401)
    return NextResponse.json({ code: result.code }, { status: result.status || 503 });
  const destination = getSafeRedirectPath(url.searchParams.get("next"), publicOrigin, "/");
  const response = new NextResponse(null, { status: 303, headers: { location: destination } });
  response.cookies.delete(SESSION_COOKIE);
  response.cookies.delete(ORG_COOKIE);
  return response;
}
