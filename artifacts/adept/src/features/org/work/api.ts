import { cache } from "react";

import { call, getApi, type Schemas } from "@/lib/api";

export type Assignment = Schemas["ProgrammeAssignment"];

/** The member's own programme assignments in the current organisation workspace. */
export const fetchMyProgrammes = cache(async function fetchMyProgrammes() {
  const api = await getApi();
  return call(api.GET("/api/v1/org/programmes/mine"));
});

/** Accepted programmes first (newest first within each group), then everything else. */
export function byStatus(assignments: Assignment[]): {
  pending: Assignment[];
  accepted: Assignment[];
  closed: Assignment[];
} {
  return {
    pending: assignments.filter((a) => a.status === "assigned" || a.status === "change_requested"),
    accepted: assignments.filter((a) => a.status === "accepted"),
    closed: assignments.filter((a) => a.status === "declined"),
  };
}
