import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "adept_session";

/**
 * Cheap gate before rendering: workspace pages need a session cookie (the API still verifies
 * the signed token on every call, and layouts send each account to its own workspace).
 * Also exposes the pathname to server layouts as `x-adept-path`.
 */
export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const headers = new Headers(request.headers);
  headers.set("x-adept-path", pathname);
  const workspace = /^\/(app|org|admin)(\/|$)/.test(pathname);
  const token = request.cookies.get(SESSION_COOKIE)?.value ?? "";
  if (workspace && process.env.AUTH_MODE !== "supabase" && !token.startsWith("v1.")) {
    const query = new URLSearchParams({
      mode: pathname.startsWith("/org") ? "organisation" : "individual",
      next: pathname + search,
    });
    const url = request.nextUrl.clone();
    url.pathname = "/auth/login";
    url.search = query.toString();
    return NextResponse.redirect(url, 303);
  }
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: ["/app/:path*", "/org/:path*", "/admin/:path*", "/auth/:path*"] };
