import { getGeneration, withBase } from "@/lib/next-compat/router";

/** Frontend-safe session view. The httpOnly session cookie never reaches this code. */
export type AuthMode = "demo" | "supabase";
export type SessionInfo = { authenticated: boolean; org?: string | null; locale?: string | null; auth_mode?: AuthMode; is_admin?: boolean };

let cached: { generation: number; promise: Promise<SessionInfo> } | undefined;
let last: SessionInfo | undefined;

export function getSession(): Promise<SessionInfo> {
  const generation = getGeneration();
  if (!cached || cached.generation !== generation) {
    const promise = fetch(withBase("/api/session"), { credentials: "include", cache: "no-store" })
      .then((r) => (r.ok ? (r.json() as Promise<SessionInfo>) : { authenticated: false }))
      .catch(() => ({ authenticated: false }))
      .then((s) => {
        last = s;
        return s;
      });
    cached = { generation, promise };
  }
  return cached.promise;
}

export function getAuthMode(): AuthMode {
  return last?.auth_mode === "supabase" ? "supabase" : "demo";
}

/** Opaque marker: truthy when signed in. Never the real token. */
export async function getSessionToken(): Promise<string | undefined> {
  return (await getSession()).authenticated ? "session" : undefined;
}
