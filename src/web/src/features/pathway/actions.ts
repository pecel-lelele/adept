"use server";

import { revalidatePath } from "next/cache";

import { getApi } from "@/lib/api";
import { parseScenario } from "@/lib/scenario";

import { actionError, type ActionState } from "./action-state";

const COURSE_STATUSES = ["not_started", "in_progress", "completed"] as const;
type CourseStatus = (typeof COURSE_STATUSES)[number];

type ApiOutcome = { error?: unknown; response: Response };

function text(form: FormData, key: string): string {
  const value = form.get(key);
  return typeof value === "string" ? value.slice(0, 120) : "";
}

/** Only refresh the page when the API accepted the change; otherwise report why not. */
async function settle(request: Promise<ApiOutcome>, path: string): Promise<ActionState> {
  try {
    const { error, response } = await request;
    if (error !== undefined || !response.ok) return { error: actionError(error, response.status) };
  } catch {
    return { error: "The API could not be reached." };
  }
  revalidatePath(path);
  return { done: Date.now() };
}

/** The learner explicitly chooses a target role and saves its plan (human in charge). */
export async function savePlanAction(_: ActionState, form: FormData): Promise<ActionState> {
  const api = await getApi();
  return settle(
    api.POST("/api/v1/pathway/plans", {
      body: { role_id: text(form, "role_id"), scenario: parseScenario(text(form, "scenario")) },
    }),
    "/app/pathway",
  );
}

export async function acceptReplanAction(): Promise<ActionState> {
  const api = await getApi();
  return settle(api.POST("/api/v1/pathway/plans/me/accept-replan"), "/app/pathway");
}

export async function updateProgressAction(_: ActionState, form: FormData): Promise<ActionState> {
  const raw = text(form, "status");
  const status: CourseStatus = COURSE_STATUSES.find((s) => s === raw) ?? "not_started";
  const api = await getApi();
  return settle(
    api.POST("/api/v1/pathway/progress", {
      params: { query: { scenario: parseScenario(text(form, "scenario")) } },
      body: { role_id: text(form, "role_id"), course_id: text(form, "course_id"), status },
    }),
    "/app/progress",
  );
}
