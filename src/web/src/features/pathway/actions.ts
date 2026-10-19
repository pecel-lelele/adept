"use server";

import { revalidatePath } from "next/cache";

import { getApi } from "@/lib/api";
import { parseScenario } from "@/lib/scenario";

const COURSE_STATUSES = ["not_started", "in_progress", "completed"] as const;
type CourseStatus = (typeof COURSE_STATUSES)[number];

function text(form: FormData, key: string): string {
  const value = form.get(key);
  return typeof value === "string" ? value.slice(0, 120) : "";
}

/** The learner explicitly chooses a target role and saves its plan (human in charge). */
export async function savePlanAction(form: FormData): Promise<void> {
  const api = await getApi();
  await api.POST("/api/v1/pathway/plans", {
    body: { role_id: text(form, "role_id"), scenario: parseScenario(text(form, "scenario")) },
  });
  revalidatePath("/app/pathway");
}

export async function acceptReplanAction(): Promise<void> {
  const api = await getApi();
  await api.POST("/api/v1/pathway/plans/me/accept-replan");
  revalidatePath("/app/pathway");
}

export async function updateProgressAction(form: FormData): Promise<void> {
  const raw = text(form, "status");
  const status: CourseStatus = COURSE_STATUSES.find((s) => s === raw) ?? "not_started";
  const api = await getApi();
  await api.POST("/api/v1/pathway/progress", {
    params: { query: { scenario: parseScenario(text(form, "scenario")) } },
    body: { role_id: text(form, "role_id"), course_id: text(form, "course_id"), status },
  });
  revalidatePath("/app/progress");
}
