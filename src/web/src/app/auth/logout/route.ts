import { NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/auth/session";

export function GET() {
  const response = new NextResponse(null, { status: 303, headers: { location: "/" } });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
