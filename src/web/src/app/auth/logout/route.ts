import { type NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/auth/session";
import { ORG_COOKIE } from "@/lib/auth/workspace";

export function GET(request: NextRequest) {
  // Allow an optional ?next= redirect so callers can land on a specific page after logout.
  // Only same-origin paths are accepted to prevent open-redirect abuse.
  const raw = request.nextUrl.searchParams.get("next") ?? "";
  const destination = raw.startsWith("/") ? raw : "/";
  const response = new NextResponse(null, { status: 303, headers: { location: destination } });
  response.cookies.delete(SESSION_COOKIE);
  response.cookies.delete(ORG_COOKIE);
  return response;
}
