import { API_URL } from "@/lib/api/client";
import { trustedClientIp } from "@/lib/api/server";
import { getSessionToken } from "@/lib/auth/session";

const PROXY_SECRET = process.env.PROXY_SHARED_SECRET ?? "";
const TRUSTED_PROXY_HOPS = Number.parseInt(process.env.TRUSTED_PROXY_HOPS ?? "0", 10) || 0;
const MAX_BYTES = 32 * 1024;

/** Relays a question to Adi with the signed-in session (httpOnly cookie) when there is one. */
export async function POST(request: Request) {
  const publicOrigin = process.env.WEB_ORIGIN ?? "http://localhost:3000";
  const origin = request.headers.get("origin");
  if (origin && origin !== publicOrigin) return new Response(null, { status: 403 });
  const text = await request.text();
  if (text.length > MAX_BYTES) return Response.json({ error: { code: "too_large", message: "Message too long." } }, { status: 413 });
  const headers: Record<string, string> = { "content-type": "application/json" };
  const token = await getSessionToken();
  if (token) headers["X-Demo-User"] = token;
  const ip = trustedClientIp(request.headers.get("x-forwarded-for"), TRUSTED_PROXY_HOPS);
  if (PROXY_SECRET && ip) {
    headers["X-Real-IP"] = ip;
    headers["X-Internal-Proxy-Secret"] = PROXY_SECRET;
  }
  try {
    const result = await fetch(`${API_URL}/api/v1/assistant/chat`, {
      method: "POST",
      body: text,
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(30000),
    });
    return new Response(await result.text(), {
      status: result.status,
      headers: { "content-type": "application/json", "cache-control": "no-store" },
    });
  } catch {
    return Response.json(
      { error: { code: "network", message: "Adi can’t reach Adept right now. Please try again." } },
      { status: 503 },
    );
  }
}
