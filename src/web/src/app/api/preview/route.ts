import { API_URL } from "@/lib/api/client";
import { trustedClientIp } from "@/lib/api/proxy";
import { proxyConfig } from "@/lib/api/proxy-config";

const MAX_BYTES = 5 * 1024 * 1024;
const { secret: PROXY_SECRET, trustedHops: TRUSTED_PROXY_HOPS, clientIpMode } = proxyConfig();

/** Anonymous CV preview from the landing page, relayed to the API from this origin only. */
export async function POST(request: Request) {
  const length = Number(request.headers.get("content-length"));
  if (!Number.isFinite(length) || length <= 0)
    return Response.json({ message: "Content length required." }, { status: 411 });
  if (length > MAX_BYTES + 65536)
    return Response.json({ message: "Use a file under 5 MB." }, { status: 413 });
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const protocol = request.headers.get("x-forwarded-proto") ?? new URL(request.url).protocol.replace(":", "");
  const publicOrigin = process.env.WEB_ORIGIN ?? `${protocol}://${host}`;
  if (request.headers.get("origin") !== publicOrigin) return new Response(null, { status: 403 });
  try {
    const form = await request.formData();
    const file = form.get("file");
    if (!(file instanceof File) || file.size > MAX_BYTES || form.get("synthetic_consent") !== "true")
      return Response.json(
        { message: "Choose a CV file and agree that we may read it." },
        { status: 422 },
      );
    // Rate limits apply per visitor, not per web server: forward the client address.
    const headers: Record<string, string> = {};
    const ip = trustedClientIp(request.headers.get("x-forwarded-for"), TRUSTED_PROXY_HOPS, clientIpMode);
    if (PROXY_SECRET && ip) {
      headers["X-Real-IP"] = ip;
      headers["X-Internal-Proxy-Secret"] = PROXY_SECRET;
    }
    const result = await fetch(API_URL + "/api/v1/preview/cv?include_suggestions=false", {
      method: "POST",
      body: form,
      headers,
      signal: AbortSignal.timeout(20000),
    });
    return new Response(await result.text(), {
      status: result.status,
      headers: { "content-type": "application/json", "cache-control": "no-store" },
    });
  } catch {
    return Response.json({ message: "Preview unavailable. Try again shortly." }, { status: 503 });
  }
}
