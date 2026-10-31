import assert from "node:assert/strict";
import test from "node:test";
import { CV_HANDOFF_KEY, clearCvHandoff, cvFile, readCvHandoff, writeCvHandoff } from "../src/web/src/features/profile/cv-handoff.ts";
import { intakeDraftKey, readIntakeDraft, writeIntakeDraft } from "../src/web/src/features/profile/intake-draft.ts";

test("handoff carries only filename metadata and confirmed catalogue levels", () => {
  const values = new Map<string, string>();
  const storage = { getItem: (k: string) => values.get(k) ?? null, setItem: (k: string, v: string) => { values.set(k, v); }, removeItem: (k: string) => { values.delete(k); } };
  const file = cvFile("C:\\fakepath\\sample_cv.pdf", true)!;
  assert.deepEqual(file, { name: "sample_cv.pdf", truncated: true });
  writeCvHandoff(storage, { file, skills: [{ skill_id: "python", level: 4 }] });
  assert.deepEqual(JSON.parse(values.get(CV_HANDOFF_KEY)!), { file, skills: [{ skill_id: "python", level: 4 }] });
  const handoff = readCvHandoff(storage, new Set(["python"]));
  assert.ok(handoff);
  const key = intakeDraftKey("synthetic-a");
  writeIntakeDraft(storage, key, {
    segment: "working", interests: [], hours_per_week: 6, budget_myr: 300, hrd_eligible: false,
    learning_style: "mixed", skills: handoff.skills.map((s) => ({ ...s, fromCv: true })), step: 4, cvFile: handoff.file,
  });
  clearCvHandoff(storage);
  assert.equal(readCvHandoff(storage, new Set(["python"])), null);
  const draft = readIntakeDraft(storage, key, new Set(["python"]), []);
  assert.deepEqual(draft?.cvFile, file);
  assert.deepEqual(draft?.skills, [{ skill_id: "python", level: 4, fromCv: true }]);
  assert.equal(readIntakeDraft(storage, intakeDraftKey("synthetic-b"), new Set(["python"]), []), null);
});

test("handoff treats browser data as untrusted and works with blocked storage", () => {
  const skills = [{ skill_id: "python", level: null }, { skill_id: "python", level: 3 }, { skill_id: "python", level: 5 }, { skill_id: "unknown", level: 4 }];
  const storage = { getItem: () => JSON.stringify({ file: { name: "sample.txt" }, skills }) };
  assert.deepEqual(readCvHandoff(storage, new Set(["python"]))?.skills, [{ skill_id: "python", level: 3 }]);
  assert.equal(readCvHandoff(storage, new Set()), null);
  assert.equal(readCvHandoff({ getItem: () => "{" }, new Set()), null);
  const blocked = () => { throw new Error("Storage disabled"); };
  assert.equal(readCvHandoff({ getItem: blocked }, new Set()), null);
  assert.doesNotThrow(() => clearCvHandoff({ removeItem: blocked }));
});
