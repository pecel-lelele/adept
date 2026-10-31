import type { IntakeInput } from "./actions";
import { cvFile, type CvFile } from "./cv-handoff.ts";

export type IntakeDraft = Omit<IntakeInput, "skills"> & {
  step: number; cvFile?: CvFile;
  skills: (IntakeInput["skills"][number] & { fromCv?: boolean })[];
};
export const intakeDraftKey = (userId: string) => `adept:intake:v1:${userId}`;

/** Browser storage is optional and untrusted; catalogue IDs are checked again on restore. */
export function readIntakeDraft(storage: Pick<Storage, "getItem">, key: string, skillIds: ReadonlySet<string>, interests: readonly string[]): IntakeDraft | null {
  try {
    const value: unknown = JSON.parse(storage.getItem(key) ?? "null");
    if (!value || typeof value !== "object") return null;
    const d = value as Record<string, unknown>;
    if (!['working', 'graduate', 'switcher'].includes(String(d.segment)) ||
      !['video', 'reading', 'hands-on', 'classroom', 'mixed'].includes(String(d.learning_style)) ||
      typeof d.hours_per_week !== "number" || !Number.isFinite(d.hours_per_week) || d.hours_per_week < 0 || d.hours_per_week > 80 ||
      typeof d.budget_myr !== "number" || !Number.isFinite(d.budget_myr) || d.budget_myr < 0 ||
      typeof d.hrd_eligible !== "boolean" || !Array.isArray(d.interests) || !Array.isArray(d.skills)) return null;
    const skills: IntakeDraft["skills"] = [];
    for (const item of d.skills) {
      if (!item || typeof item !== "object") continue;
      const s = item as Record<string, unknown>;
      if (typeof s.skill_id === "string" && skillIds.has(s.skill_id) && typeof s.level === "number" &&
        Number.isInteger(s.level) && s.level >= 1 && s.level <= 5 && !skills.some((picked) => picked.skill_id === s.skill_id)) {
        skills.push({ skill_id: s.skill_id, level: s.level, ...(s.fromCv === true ? { fromCv: true } : {}) });
      }
    }
    const metadata = d.cvFile && typeof d.cvFile === "object" ? d.cvFile as Record<string, unknown> : null;
    const file = metadata ? cvFile(metadata.name, metadata.truncated === true) : null;
    return {
      segment: d.segment as IntakeInput["segment"], learning_style: d.learning_style as IntakeInput["learning_style"],
      hours_per_week: d.hours_per_week, budget_myr: d.budget_myr, hrd_eligible: d.hrd_eligible,
      interests: d.interests.filter((i): i is string => typeof i === "string" && interests.includes(i)), skills,
      step: typeof d.step === "number" && Number.isInteger(d.step) ? d.step : 1,
      ...(file ? { cvFile: file } : {}),
    };
  } catch {
    return null;
  }
}

export function writeIntakeDraft(storage: Pick<Storage, "setItem">, key: string, draft: IntakeDraft): void {
  try { storage.setItem(key, JSON.stringify(draft)); } catch { /* Storage disabled or full. */ }
}

export function clearIntakeDraft(storage: Pick<Storage, "removeItem">, key: string): void {
  try { storage.removeItem(key); } catch { /* Storage disabled. */ }
}
