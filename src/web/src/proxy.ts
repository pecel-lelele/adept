import { NextResponse, type NextRequest } from "next/server";
export function proxy(request: NextRequest) {
  if (process.env.AUTH_MODE === "supabase") return NextResponse.next();
  const user = request.cookies.get("adept_demo")?.value;
  const org = request.nextUrl.pathname.startsWith("/org");
  const valid = [
    "aisyah",
    "weijie",
    "ravi",
    "demo-company",
    "demo-institution",
  ].includes(user ?? "");
  const admin = user === "demo-company" || user === "demo-institution";
  if (!valid) {
    const query = new URLSearchParams({
      mode: org ? "organisation" : "individual",
      next: request.nextUrl.pathname + request.nextUrl.search,
    });
    return NextResponse.redirect(
      new URL(
        "/auth/login?" + query.toString(),
        process.env.WEB_ORIGIN ?? "http://localhost:3000",
      ),
      303,
    );
  }
  if (org !== admin)
    return NextResponse.redirect(
      new URL(
        admin ? "/org" : "/app",
        process.env.WEB_ORIGIN ?? "http://localhost:3000",
      ),
      303,
    );
  return NextResponse.next();
}
export const config = { matcher: ["/app/:path*", "/org/:path*"] };
