import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

test("guest PDF filename and ratings survive signup, reload and replacement in onboarding", async ({ page }) => {
  await page.goto("/");
  const preview = page.locator("#start.a-upload");
  await preview.locator('input[type="file"]').setInputFiles({
    name: "sample_cv.pdf", mimeType: "application/pdf",
    buffer: readFileSync("docs/demo-cvs/cv_sofia_tan_process_automation_analyst.pdf"),
  });
  await preview.getByRole("checkbox").check();
  await preview.getByRole("button", { name: "Upload CV", exact: true }).click();
  await expect(preview.locator(".cv-rating-row").first()).toBeVisible();
  const rows = await preview.locator(".cv-rating-row").all();
  for (let n = 0; n < rows.length; n++) await rows[n]!.getByRole("button", { name: `Level ${n % 5 + 1}`, exact: true }).click();
  await preview.getByRole("button", { name: "Save and see my skills outlook", exact: true }).click();
  await expect(preview.getByRole("heading", { name: "See your full results", exact: true })).toBeVisible();
  const expected = await page.evaluate(() => JSON.parse(sessionStorage.getItem("adept:cv-handoff:v1") ?? "null") as { file: { name: string }; skills: { skill_id: string; level: number }[] });
  expect(expected.file.name).toBe("sample_cv.pdf");
  await preview.getByRole("link", { name: "Create free account", exact: true }).click();
  const form = page.locator(".a-auth-form");
  await form.locator('[name="display_name"]').fill("Synthetic CV Handoff Learner");
  await form.locator('[name="email"]').fill(`handoff-${test.info().project.name}-${Date.now()}@example.test`);
  await form.locator('[name="password"]').fill("synthetic-handoff-password");
  await form.locator('[name="consent"]').check();
  await form.locator('button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\/onboarding/);
  for (let n = 0; n < 3; n++) await page.getByRole("button", { name: "Continue", exact: true }).click();
  const wizard = page.locator(".a-wizard");
  await expect(wizard.locator("[data-cv-file]")).toContainText("sample_cv.pdf");
  await expect(wizard.locator(".a-drop")).toHaveCount(0);
  await expect(wizard.locator(".a-skillrow")).toHaveCount(expected.skills.length);
  expect(await wizard.locator('.a-levels button[aria-pressed="true"]').allTextContents()).toEqual(expected.skills.map((s) => String(s.level)));
  expect(await page.evaluate(() => sessionStorage.getItem("adept:cv-handoff:v1"))).toBeNull();
  await page.reload();
  await expect(wizard.locator("[data-cv-file]")).toContainText("sample_cv.pdf");
  expect(await wizard.locator('.a-levels button[aria-pressed="true"]').allTextContents()).toEqual(expected.skills.map((s) => String(s.level)));
  await wizard.locator('input[type="file"]').setInputFiles({ name: "invalid.html", mimeType: "text/html", buffer: Buffer.from("Synthetic invalid format") });
  await expect(wizard.getByRole("alert")).toBeVisible();
  await expect(wizard.locator("[data-cv-file]")).toContainText("sample_cv.pdf");
  await expect(wizard.locator(".a-skillrow")).toHaveCount(expected.skills.length);
  await wizard.locator('input[type="file"]').setInputFiles({ name: "replacement.txt", mimeType: "text/plain", buffer: Buffer.from("SYNTHETIC CV\nSkills\nSQL\n") });
  await expect(wizard.locator("[data-cv-file]")).toContainText("replacement.txt");
  await expect(wizard.locator(".a-skillrow")).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await wizard.screenshot({ path: `tmp/cv-onboarding-${test.info().project.name}.png` });
  await wizard.getByRole("button", { name: "Save and see my skills outlook", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/radar/);
  expect(await page.evaluate(() => Object.keys(sessionStorage).some((key) => key.startsWith("adept:intake:v1:")))).toBe(false);
});
