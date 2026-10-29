import { cookies } from "next/headers";

/** httpOnly cookie holding the API-signed session token (never a raw user id). */
export const SESSION_COOKIE = "adept_session";
const TOKEN_PREFIX = "v1.";
const MAX_AGE_S = 14 * 24 * 3600; // matches the API token lifetime

export async function getSessionToken(): Promise<string | undefined> {
  const value = (await cookies()).get(SESSION_COOKIE)?.value;
  return value?.startsWith(TOKEN_PREFIX) ? value : undefined;
}

export async function setSessionToken(token: string): Promise<void> {
  (await cookies()).set(SESSION_COOKIE, token, {
    path: "/",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: MAX_AGE_S,
  });
}

export async function clearSession(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}
