import { call, getApi, type Schemas } from "@/lib/api";

export type ProgrammeOptions = Schemas["ProgrammeOptions"];
export type ProgrammeBrief = Schemas["ProgrammeBriefIn"];
export type ProgrammePlan = Schemas["ProgrammePlan"];
export type ProgrammeStatus = Schemas["ProgrammeStatus"];

/** What HR can build a programme from: objectives, roles with team readiness, sharing members. */
export async function fetchProgrammeOptions() {
  const api = await getApi();
  return call(api.GET("/api/v1/org/programmes/options"));
}

/** Programmes sent by this organisation, newest first, with each member's answer. */
export async function fetchProgrammes() {
  const api = await getApi();
  return call(api.GET("/api/v1/org/programmes"));
}
