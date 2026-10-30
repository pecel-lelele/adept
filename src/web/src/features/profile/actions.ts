"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { API_URL, call, getApi, type Schemas } from "@/lib/api";
import { errorBody } from "@/lib/api/client";
import { getSessionToken } from "@/lib/auth/session";

export type IntakeInput = {
  segment: "working" | "graduate" | "switcher";
  interests: string[];
  hours_per_week: number;
  budget_myr: number;
  hrd_eligible: boolean;
  learning_style: "video" | "reading" | "hands-on" | "classroom" | "mixed";
  skills: { skill_id: string; level: number }[];
};

export type IntakeResult = { error?: string };
export type CvResult = { error?: string } & Partial<Pick<Schemas["CvExtractionResult"], "skills" | "unmatched_terms" | "suggestions" | "truncated">>;

/** Only invoked by an explicit search submission; API authentication remains authoritative. */
export async function resolveSkillAction(query: string) {
  const api = await getApi();
  return call(api.POST("/api/v1/profile/skills/resolve", { body: { query } }));
}

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, Math.round(n || 0)));

/** Save the questionnaire, then the confirmed skills. Both land in PostgreSQL. */
export async function saveIntakeAction(input: IntakeInput): Promise<IntakeResult> {
  if (!input.skills.length) return { error: "skill_required" };
  const api = await getApi();
  const profile = await call(
    api.POST("/api/v1/profile/questionnaire", {
      body: {
        segment: input.segment,
        interests: input.interests.slice(0, 20).map((i) => i.slice(0, 40)),
        hours_per_week: clamp(input.hours_per_week, 0, 80),
        budget_myr: clamp(input.budget_myr, 0, 100000),
        hrd_eligible: Boolean(input.hrd_eligible),
        learning_style: input.learning_style,
      },
    }),
  );
  if (!profile.ok) return { error: profile.code };
  const skills = await call(
    api.PUT("/api/v1/profile/skills/confirm", {
      body: {
        // Every selected skill is saved (the picker offers the whole catalogue); only
        // duplicates are dropped.
        skills: [...new Map(input.skills.map((s) => [s.skill_id, s])).values()].map((s) => ({
          skill_id: s.skill_id,
          level: clamp(s.level, 1, 5),
          source: "confirmed" as const,
        })),
      },
    }),
  );
  if (!skills.ok) return { error: skills.code };
  revalidatePath("/app", "layout");
  revalidatePath("/org", "layout");
  // Intake leads to the Radar first (which skills are rising), then on to matches.
  redirect("/app/radar");
}

/** Forward a CV to the parser. The file is processed in memory by the API and never stored. */
export async function uploadCvAction(form: FormData): Promise<CvResult> {
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0) return { error: "choose_file" };
  if (file.size > 5 * 1024 * 1024) return { error: "payload_too_large" };
  const token = await getSessionToken();
  const body = new FormData();
  body.set("file", file, file.name);
  try {
    const response = await fetch(`${API_URL}/api/v1/profile/cv?include_suggestions=false`, {
      method: "POST",
      body,
      headers: token ? { "X-Demo-User": token } : {},
      signal: AbortSignal.timeout(30000),
      cache: "no-store",
    });
    const json: unknown = await response.json().catch(() => null);
    if (!response.ok) return { error: errorBody(json, response.status).code };
    const parsed = json as Schemas["CvExtractionResult"];
    return { skills: parsed.skills, unmatched_terms: parsed.unmatched_terms, suggestions: parsed.suggestions, truncated: parsed.truncated };
  } catch {
    return { error: "cv_read_failed" };
  }
}
