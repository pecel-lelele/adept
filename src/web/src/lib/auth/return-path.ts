import { headers } from "next/headers";

import { safeReturn } from "@/lib/navigation";

export async function currentPath(fallback: string): Promise<string> {
  const incoming = await headers();
  return safeReturn(
    (incoming.get("x-adept-path") ?? fallback) + (incoming.get("x-adept-search") ?? ""),
    fallback.startsWith("/org") ? "organisation" : "individual",
  );
}

export async function loginHref(fallback: string): Promise<string> {
  return `/auth/login?${new URLSearchParams({
    mode: fallback.startsWith("/org") ? "organisation" : "individual",
    next: await currentPath(fallback),
  })}`;
}
