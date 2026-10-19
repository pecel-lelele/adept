import { NextResponse, type NextRequest } from "next/server";

import { DEMO_COOKIE, DEMO_PERSONAS, getAuthMode } from "./session";

/** Route handler body for /demo/learner and /demo/org (AUTH_MODE=demo only). */
export function demoSignIn(request: NextRequest, persona: keyof typeof DEMO_PERSONAS) {
  if (getAuthMode() !== "demo") {
    return NextResponse.redirect(new URL("/auth/login", request.url));
  }
  const { id, home } = DEMO_PERSONAS[persona];
  const response = NextResponse.redirect(new URL(home, request.url));
  response.cookies.set(DEMO_COOKIE, id, { path: "/", httpOnly: true, sameSite: "lax" });
  return response;
}
