import { NextResponse, type NextRequest } from "next/server";

import { DEMO_COOKIE, DEMO_PERSONAS, getAuthMode } from "./session";
import { safeReturn } from "@/lib/navigation";

/** Route handler body for /demo/learner and /demo/org (AUTH_MODE=demo only). */
export function demoSignIn(
  request: NextRequest,
  persona: keyof typeof DEMO_PERSONAS,
) {
  if (getAuthMode() !== "demo") {
    return new NextResponse(null, {
      status: 303,
      headers: { location: "/auth/login" },
    });
  }
  const { id, home } = DEMO_PERSONAS[persona];
  const next = request.nextUrl.searchParams.get("next");
  const mode = persona === "org" ? "organisation" : "individual";
  const response = new NextResponse(null, {
    status: 303,
    headers: { location: next ? safeReturn(next, mode) : home },
  });
  response.cookies.set(DEMO_COOKIE, id, {
    path: "/",
    httpOnly: true,
    sameSite: "lax",
  });
  return response;
}
