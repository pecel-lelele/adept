import { API_URL } from "@/lib/api/client";
import { clientIpHeaders } from "@/lib/api/proxy";
import { proxyConfig } from "@/lib/api/proxy-config";

const MAX_BYTES = 5 * 1024 * 1024;
const proxy = proxyConfig();

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
    const headers = clientIpHeaders(request.headers.get("x-forwarded-for"), proxy);
    const result = await fetch(API_URL + "/api/v1/preview/cv?include_suggestions=false&extract_only=true", {
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

/** Re-score only confirmed catalogue IDs and levels; the CV is never resent or saved. */
export async function PUT(request: Request) {
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const protocol = request.headers.get("x-forwarded-proto") ?? new URL(request.url).protocol.replace(":", "");
  const publicOrigin = process.env.WEB_ORIGIN ?? `${protocol}://${host}`;
  if (request.headers.get("origin") !== publicOrigin) return new Response(null, { status: 403 });
  const rawLength = request.headers.get("content-length");
  if (rawLength !== null && (!/^\d+$/.test(rawLength) || Number(rawLength) > 32768))
    return Response.json({ message: "Invalid assessment size." }, { status: 413 });
  try {
    // HTTP/2 and streaming proxies may omit Content-Length. Bound the actual bytes
    // instead of rejecting a valid assessment or trusting an understated header.
    const reader = request.body?.getReader();
    if (!reader) return Response.json({ message: "Assessment required." }, { status: 400 });
    const decoder = new TextDecoder();
    let text = "";
    let bytes = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        if (bytes > 32768) {
          await reader.cancel();
          return Response.json({ message: "Invalid assessment size." }, { status: 413 });
        }
        text += decoder.decode(value, { stream: true });
      }
      text += decoder.decode();
    } finally {
      reader.releaseLock();
    }
    let data: unknown;
    try { data = JSON.parse(text); }
    catch { return Response.json({ message: "Invalid assessment JSON." }, { status: 400 }); }
    const result = await fetch(API_URL + "/api/v1/preview/cv/confirm", {
      method: "POST",
      body: JSON.stringify(data),
      headers: { ...clientIpHeaders(request.headers.get("x-forwarded-for"), proxy), "content-type": "application/json" },
      signal: AbortSignal.timeout(20000),
    });
    return new Response(await result.text(), {
      status: result.status,
      headers: { "content-type": "application/json", "cache-control": "no-store" },
    });
  } catch {
    return Response.json({ message: "Outlook unavailable. Try again shortly." }, { status: 503 });
  }
}
