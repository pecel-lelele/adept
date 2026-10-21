import { NextResponse } from "next/server";
import { DEMO_COOKIE } from "@/lib/auth/session";
export function GET() {
  const response = new NextResponse(null, {
    status: 303,
    headers: { location: "/" },
  });
  response.cookies.delete(DEMO_COOKIE);
  return response;
}
