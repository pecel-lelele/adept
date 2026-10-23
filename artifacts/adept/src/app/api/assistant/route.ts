import { API_URL } from "@/lib/api/client";
import { trustedClientIp } from "@/lib/api/server";
import { getSessionToken } from "@/lib/auth/session";
import { selectedOrg, workspaceFor } from "@/lib/auth/workspace";

const PROXY_SECRET = process.env.PROXY_SHARED_SECRET ?? "";
const TRUSTED_PROXY_HOPS = Number.parseInt(process.env.TRUSTED_PROXY_HOPS ?? "0", 10) || 0;
const MAX_BYTES = 32 * 1024;

const tooLarge = () =>
  Response.json({ error: { code: "too_large", message: "Message too long." } }, { status: 413 });

/** Read at most MAX_BYTES of the body, stopping as soon as the limit is passed. */
async function readCapped(request: Request): Promise<string | null> {
  const declared = Number(request.headers.get("content-length"));
  if (Number.isFinite(declared) && declared > MAX_BYTES) return null;
  if (!request.body) return "";
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BYTES) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  const all = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    all.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder().decode(all);
}

function pageOf(body: string): string {
  try {
    const page = (JSON.parse(body) as { page?: unknown }).page;
    return typeof page === "string" ? page : "";
  } catch {
    return "";
  }
}

/** Relays a question to Adi with the signed-in session (httpOnly cookie) when there is one. */
export async function POST(request: Request) {
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const protocol = request.headers.get("x-forwarded-proto") ?? new URL(request.url).protocol.replace(":", "");
  const publicOrigin = process.env.WEB_ORIGIN ?? `${protocol}://${host}`;
  const origin = request.headers.get("origin");
  if (origin && origin !== publicOrigin) return new Response(null, { status: 403 });
  const token = await getSessionToken();
  if (!token) return Response.json({ error: { code: "unauthorized", message: "Please sign in." } }, { status: 401 });
  const text = await readCapped(request);
  if (text === null) return tooLarge();
  const headers: Record<string, string> = { "content-type": "application/json" };
  headers["X-Demo-User"] = token;
  // Adi answers inside the workspace of the page the question was asked on.
  const workspace = workspaceFor(pageOf(text), await selectedOrg());
  if (workspace) headers["X-Workspace"] = workspace;
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
