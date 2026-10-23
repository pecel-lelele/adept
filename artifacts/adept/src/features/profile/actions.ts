import type { Schemas } from "@/lib/api";
import { rpc } from "@/lib/next-compat/rpc";

const M = "features/profile/actions.ts";

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

/** Save the questionnaire, then the confirmed skills. */
export async function saveIntakeAction(input: IntakeInput): Promise<IntakeResult> {
  return rpc(M, "saveIntakeAction", [input]);
}
/** Forward a CV to the parser. The file is processed in memory by the API and never stored. */
export async function uploadCvAction(form: FormData): Promise<CvResult> {
  return rpc(M, "uploadCvAction", [form], false);
}
