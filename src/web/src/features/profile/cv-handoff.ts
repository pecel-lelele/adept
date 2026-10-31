/** Same-tab guest handoff: filename and confirmed catalogue levels only, never file bytes. */
export const CV_SKILLS_KEY = "adept.cv-skills";
export const CV_HANDOFF_KEY = "adept:cv-handoff:v1";
export type CvFile = { name: string; truncated: boolean };
export type ConfirmedCvSkill = { skill_id: string; level: number };
export type CvHandoff = { file: CvFile; skills: ConfirmedCvSkill[] };

export function cvFile(name: unknown, truncated = false): CvFile | null {
  if (typeof name !== "string") return null;
  const safe = (name.split(/[\\/]/).at(-1) ?? "").replace(/\p{Cc}/gu, "").trim().slice(0, 200);
  return safe ? { name: safe, truncated } : null;
}

export function confirmedCvSkills(value: unknown, known: ReadonlySet<string>): ConfirmedCvSkill[] {
  if (!Array.isArray(value) || value.length > 200) return [];
  const picked: ConfirmedCvSkill[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") continue;
    const skill = item as Record<string, unknown>;
    if (typeof skill.skill_id === "string" && known.has(skill.skill_id) &&
        typeof skill.level === "number" && Number.isInteger(skill.level) && skill.level >= 1 && skill.level <= 5 &&
        !picked.some((s) => s.skill_id === skill.skill_id)) {
      picked.push({ skill_id: skill.skill_id, level: skill.level });
    }
  }
  return picked;
}

export function readCvHandoff(storage: Pick<Storage, "getItem">, known: ReadonlySet<string>): CvHandoff | null {
  try {
    const value: unknown = JSON.parse(storage.getItem(CV_HANDOFF_KEY) ?? "null");
    if (!value || typeof value !== "object") return null;
    const data = value as Record<string, unknown>;
    if (!data.file || typeof data.file !== "object") return null;
    const metadata = data.file as Record<string, unknown>;
    const file = cvFile(metadata.name, metadata.truncated === true);
    const skills = confirmedCvSkills(data.skills, known);
    return file && skills.length ? { file, skills } : null;
  } catch { return null; }
}

export function writeCvHandoff(storage: Pick<Storage, "setItem">, handoff: CvHandoff): void {
  try { storage.setItem(CV_HANDOFF_KEY, JSON.stringify(handoff)); } catch { /* Storage optional. */ }
}

export function clearCvHandoff(storage: Pick<Storage, "removeItem">): void {
  try { storage.removeItem(CV_HANDOFF_KEY); } catch { /* Storage optional. */ }
}
