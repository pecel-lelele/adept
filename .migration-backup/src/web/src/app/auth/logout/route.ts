import { NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/auth/session";
import { ORG_COOKIE } from "@/lib/auth/workspace";

export function GET() {
  const response = new NextResponse(null, { status: 303, headers: { location: "/" } });
  response.cookies.delete(SESSION_COOKIE);
  response.cookies.delete(ORG_COOKIE);
  return response;
}
