"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { getApi } from "@/lib/api";
import { isOrgId, PERSONAL } from "@/lib/auth/workspace";
import { parseScenario } from "@/lib/scenario";

import { actionError, type ActionState } from "./action-state";

const COURSE_STATUSES = ["not_started", "in_progress", "completed"] as const;
type CourseStatus = (typeof COURSE_STATUSES)[number];

type ApiOutcome = { error?: unknown; response: Response };

function text(form: FormData, key: string): string {
  const value = form.get(key);
  return typeof value === "string" ? value.slice(0, 120) : "";
}

/**
 * API client bound to the workspace the form was rendered for, not whatever workspace another
 * tab selected since. The API re-checks membership of the named organisation.
 */
async function apiFor(form: FormData) {
  const raw = form.get("workspace");
  const workspace = raw === PERSONAL || (typeof raw === "string" && isOrgId(raw)) ? raw : undefined;
  return getApi(workspace ? { workspace } : undefined);
}

/** Only refresh the page when the API accepted the change; otherwise report why not. */
async function settle(
  request: Promise<ApiOutcome>,
  path: string,
  type?: "layout" | "page",
): Promise<ActionState> {
  try {
    const { error, response } = await request;
    if (error !== undefined || !response.ok)
      return { error: actionError(error, response.status) };
  } catch {
    return { error: "Your change couldn’t be saved. Please try again." };
  }
  revalidatePath(path, type);
  revalidatePath("/app", "layout");
  revalidatePath("/work", "layout");
  return { done: Date.now() };
}

/** The learner explicitly chooses a target role and saves its plan (human in charge). */
export async function savePlanAction(
  _: ActionState,
  form: FormData,
): Promise<ActionState> {
  const api = await getApi();
  const outcome = await settle(
    api.POST("/api/v1/pathway/plans", {
      body: {
        role_id: text(form, "role_id"),
        scenario: parseScenario(text(form, "scenario")),
      },
    }),
    "/app/pathway",
    "layout", // also refreshes /app/pathway/compare, where the learner can choose a role
  );
  if (outcome.error) return outcome;
  redirect(
    `/app/pathway?role=${encodeURIComponent(text(form, "role_id"))}&scenario=${parseScenario(text(form, "scenario"))}`,
  );
}

export async function acceptReplanAction(): Promise<ActionState> {
  const api = await getApi();
  return settle(
    api.POST("/api/v1/pathway/plans/me/accept-replan"),
    "/app/pathway",
  );
}

export async function updateProgressAction(
  _: ActionState,
  form: FormData,
): Promise<ActionState> {
  const raw = text(form, "status");
  const status: CourseStatus =
    COURSE_STATUSES.find((s) => s === raw) ?? "not_started";
  const api = await apiFor(form);
  return settle(
    api.POST("/api/v1/pathway/progress", {
      params: { query: { scenario: parseScenario(text(form, "scenario")) } },
      body: {
        role_id: text(form, "role_id"),
        course_id: text(form, "course_id"),
        status,
      },
    }),
    "/app/progress",
  );
}

/** Learner attaches a certificate link; the API checks it against the provider's pages. */
export async function submitEvidenceAction(
  _: ActionState,
  form: FormData,
): Promise<ActionState> {
  const api = await apiFor(form);
  return settle(
    api.POST("/api/v1/pathway/progress/evidence", {
      params: { query: { scenario: parseScenario(text(form, "scenario")) } },
      body: {
        role_id: text(form, "role_id"),
        course_id: text(form, "course_id"),
        url: (form.get("url")?.toString() ?? "").slice(0, 500),
      },
    }),
    "/app/progress",
  );
}

/** HR / advisor confirms or rejects a member's completion. */
export async function reviewCompletionAction(
  _: ActionState,
  form: FormData,
): Promise<ActionState> {
  const decision = text(form, "decision") === "reject" ? "reject" : "confirm";
  const api = await apiFor(form);
  return settle(
    api.POST("/api/v1/pathway/verifications", {
      body: {
        user_id: text(form, "user_id"),
        role_id: text(form, "role_id"),
        course_id: text(form, "course_id"),
        decision,
        note: (form.get("note")?.toString() ?? "").slice(0, 300),
        submitted_at: text(form, "submitted_at") || null,
      },
    }),
    "/org/verify",
  );
}

/** Member, in the organisation workspace: share a personally completed course with the programme. */
export async function shareCompletionAction(
  _: ActionState,
  form: FormData,
): Promise<ActionState> {
  const api = await apiFor(form);
  return settle(
    api.POST("/api/v1/pathway/progress/share", {
      params: { query: { scenario: parseScenario(text(form, "scenario")) } },
      body: { role_id: text(form, "role_id"), course_id: text(form, "course_id") },
    }),
    "/work/progress",
  );
}
