import { cookies } from "next/headers";

export const DEMO_COOKIE = "adept_demo";

export type AuthMode = "demo" | "supabase";

export const DEMO_PERSONAS = {
  learner: { id: "aisyah", home: "/app" },
  org: { id: "demo-company", home: "/org" },
} as const;

export function getAuthMode(): AuthMode {
  return process.env.AUTH_MODE === "supabase" ? "supabase" : "demo";
}

export async function getDemoUser(): Promise<string | undefined> {
  return (await cookies()).get(DEMO_COOKIE)?.value;
}
