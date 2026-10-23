"use server";

import { revalidatePath } from "next/cache";

import { call, getApi } from "@/lib/api";

import type { ProgrammeBrief, ProgrammePlan } from "./api";

export type GenerateResult = { plan: ProgrammePlan; error?: undefined } | { plan?: undefined; error: string };
export type SendResult = { sent: true; error?: undefined } | { sent?: false; error: string; stale?: boolean };

/** Propose personal routes for the brief. Nothing is sent or stored. */
export async function generateProgrammeAction(brief: ProgrammeBrief): Promise<GenerateResult> {
  const api = await getApi();
  const result = await call(api.POST("/api/v1/org/programmes/generate", { body: brief }));
  return result.ok ? { plan: result.data } : { error: result.message };
}

/** Send the reviewed plan. The API refuses it if members, prices or budgets changed since. */
export async function sendProgrammeAction(brief: ProgrammeBrief, token: string): Promise<SendResult> {
  const api = await getApi();
  const result = await call(api.POST("/api/v1/org/programmes", { body: { brief, token } }));
  if (!result.ok) return { error: result.message, stale: result.status === 409 };
  revalidatePath("/org", "layout");
  return { sent: true };
}
