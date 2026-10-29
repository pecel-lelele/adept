"use server";

import { revalidatePath } from "next/cache";

import { call, getApi } from "@/lib/api";

import type { ProgrammeBrief, ProgrammePlan } from "./api";

export type GenerateResult = { plan: ProgrammePlan; error?: undefined } | { plan?: undefined; error: string };
export type SendResult = { sent: true; error?: undefined } | { sent?: false; error: string; stale?: boolean };

/** Propose personal routes for the brief. Nothing is sent or stored. */
export async function generateProgrammeAction(brief: ProgrammeBrief, expectedOrg?: string): Promise<GenerateResult> {
  const api = await getApi(expectedOrg ? { workspace: expectedOrg } : undefined);
  const result = await call(
    api.POST("/api/v1/org/programmes/generate", {
      params: expectedOrg ? { query: { expected_org: expectedOrg } } : undefined,
      body: brief,
    }),
  );
  return result.ok ? { plan: result.data } : { error: result.code };
}

/** Send the reviewed plan. The API refuses it if members, prices or budgets changed since. */
export async function sendProgrammeAction(brief: ProgrammeBrief, token: string, expectedOrg?: string): Promise<SendResult> {
  const api = await getApi(expectedOrg ? { workspace: expectedOrg } : undefined);
  const result = await call(
    api.POST("/api/v1/org/programmes", {
      params: expectedOrg ? { query: { expected_org: expectedOrg } } : undefined,
      body: { brief, token },
    }),
  );
  if (!result.ok) return { error: result.code, stale: result.status === 409 };
  revalidatePath("/org", "layout");
  return { sent: true };
}
