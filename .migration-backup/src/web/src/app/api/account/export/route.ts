import { API_URL } from "@/lib/api/client";
import { getSessionToken } from "@/lib/auth/session";

/** Download everything Adept stores about the signed-in person (PDPA access request). */
export async function GET() {
  const token = await getSessionToken();
  if (!token) return new Response(null, { status: 401 });
  try {
    const result = await fetch(`${API_URL}/api/v1/auth/me/export`, {
      headers: { "X-Demo-User": token },
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    if (!result.ok) return new Response(null, { status: result.status });
    return new Response(await result.text(), {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "content-disposition": 'attachment; filename="adept-my-data.json"',
        "cache-control": "no-store",
      },
    });
  } catch {
    return new Response(null, { status: 503 });
  }
}
