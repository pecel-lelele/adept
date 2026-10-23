import { rpc } from "@/lib/next-compat/rpc";

import type { ProgrammeBrief, ProgrammePlan } from "./api";

const M = "features/org/programmes/actions.ts";

export type GenerateResult = { plan: ProgrammePlan; error?: undefined } | { plan?: undefined; error: string };
export type SendResult = { sent: true; error?: undefined } | { sent?: false; error: string; stale?: boolean };

/** Propose personal routes for the brief. Nothing is sent or stored. */
export async function generateProgrammeAction(brief: ProgrammeBrief, expectedOrg?: string): Promise<GenerateResult> {
  return rpc(M, "generateProgrammeAction", [brief, expectedOrg], false);
}
/** Send the reviewed plan. The API refuses it if members, prices or budgets changed since. */
export async function sendProgrammeAction(brief: ProgrammeBrief, token: string, expectedOrg?: string): Promise<SendResult> {
  return rpc(M, "sendProgrammeAction", [brief, token, expectedOrg]);
}
