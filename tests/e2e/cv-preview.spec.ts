import { expect, test } from "@playwright/test";

test("CV outlook requires all ratings, recalculates on edit and hands off only saved levels", async ({ page }) => {
  let uploads = 0;
  let saves = 0;
  let failSave = false;
  await page.route("**/api/preview", async (route) => {
    if (route.request().method() === "POST") uploads++;
    else if (route.request().method() === "PUT") {
      saves++;
      if (failSave) { await route.fulfill({ status: 503, json: { message: "Synthetic failure" } }); return; }
    }
    await route.continue();
  });
  await page.goto("/");
  const preview = page.locator("#start.a-upload");
  const gate = preview.getByRole("heading", { name: "See your full results", exact: true });
  const save = preview.getByRole("button", { name: "Save and see my skills outlook", exact: true });
  await expect(gate).toHaveCount(0);
  await preview.locator('input[type="file"]').setInputFiles({
    name: "synthetic-skills.txt", mimeType: "text/plain",
    buffer: Buffer.from("SYNTHETIC CV - no personal data\nSkills\nPython; SQL; Excel; Power BI; Process mapping; RPA; Prompt engineering\n"),
  });
  await preview.getByRole("checkbox").check();
  await preview.getByRole("button", { name: "Upload CV", exact: true }).click();
  const rows = preview.locator(".cv-rating-row");
  await expect(rows).toHaveCount(7);
  expect(await rows.first().getByRole("button").first().evaluate((el) => el.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
  await expect(preview.getByRole("status")).toContainText("0/7 rated");
  await expect(preview.locator('[aria-pressed="true"]')).toHaveCount(0);
  await expect(gate).toHaveCount(0);
  await preview.screenshot({ path: `tmp/cv-rating-${test.info().project.name}.png`, style: ".a-site-head { visibility: hidden !important; }" });
  await save.click();
  await expect(preview.getByRole("alert")).toHaveText("Please rate every skill before saving.");
  expect(saves).toBe(0);
  for (let n = 0; n < 6; n++) await rows.nth(n).getByRole("button", { name: "Level 1", exact: true }).click();
  await expect(preview.getByRole("status")).toContainText("6/7 rated");
  await save.click();
  expect(saves).toBe(0);
  await rows.nth(6).getByRole("button", { name: "Level 2", exact: true }).click();
  await expect(preview.getByRole("status")).toContainText("7/7 rated");
  await expect(gate).toHaveCount(0);
  failSave = true;
  await save.click();
  // A signed-out visitor gets the log-in gate, with neutral shapes and no outlook behind it.
  const guestGate = preview.locator(".cv-outlook-gate");
  await expect(guestGate.getByRole("heading", { name: "Log in to unlock your skills outlook", exact: true })).toBeVisible();
  await expect(preview.getByRole("alert")).toHaveCount(0);
  await expect(gate).toHaveCount(0);
  await expect(preview.locator(".a-ring-label, .cv-assessment")).toHaveCount(0);
  await expect(guestGate.locator(".a-locked-content")).toHaveAttribute("aria-hidden", "true");
  expect((await guestGate.locator(".a-locked-content").textContent())?.trim()).toBe("");
  await expect(guestGate.getByRole("link", { name: "Create free account", exact: true })).toHaveAttribute("href", "/auth/signup?next=/app/onboarding");
  await expect(guestGate.getByRole("link", { name: "Log in to unlock", exact: true })).toHaveAttribute("href", "/auth/login");
  const gatedHandoff = await page.evaluate(() => JSON.parse(sessionStorage.getItem("adept:cv-handoff:v1") ?? "null") as { skills: { level: number }[] } | null);
  expect(gatedHandoff?.skills.map((s) => s.level).sort()).toEqual([1, 1, 1, 1, 1, 1, 2]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await preview.screenshot({ path: `tmp/cv-guest-gate-${test.info().project.name}.png`, style: ".a-site-head { visibility: hidden !important; }" });
  await preview.getByRole("button", { name: "Edit skill levels", exact: true }).click();
  await expect(guestGate).toHaveCount(0);
  await expect(preview.locator('[aria-pressed="true"]')).toHaveCount(7);
  await expect(gate).toHaveCount(0);
  failSave = false;
  await save.click();
  await expect(gate).toBeVisible();
  await expect(preview.locator('[data-kind="gaps"] li')).toHaveCount(7);
  await expect(preview.locator('[data-kind="strengths"] li')).toHaveCount(0);
  const score = preview.locator(".a-ring-label strong");
  const lowScore = Number((await score.textContent())?.replace("%", ""));
  const saved = () => page.evaluate(() => JSON.parse(localStorage.getItem("adept.cv-skills") ?? "null") as { skill_id: string; level: number }[] | null);
  expect((await saved())?.map((s) => s.level).sort()).toEqual([1, 1, 1, 1, 1, 1, 2]);
  await preview.getByRole("button", { name: "Edit skill levels", exact: true }).click();
  await expect(gate).toHaveCount(0);
  await expect(preview.locator('[aria-pressed="true"]')).toHaveCount(7);
  expect(await saved()).toBeNull();
  for (const row of await rows.all()) await row.getByRole("button", { name: "Level 5", exact: true }).click();
  await save.click();
  await expect(gate).toBeVisible();
  expect(Number((await score.textContent())?.replace("%", ""))).toBeGreaterThan(lowScore);
  await expect(preview.locator('[data-kind="strengths"] li')).toHaveCount(7);
  await expect(preview.locator('[data-kind="gaps"] li')).toHaveCount(0);
  expect((await saved())?.every((s) => s.level === 5)).toBe(true);
  const assessmentColumns = await preview.locator(".cv-assessment").evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(" ").length);
  expect(assessmentColumns).toBe(test.info().project.name === "desktop" ? 2 : 1);
  const gapBox = await preview.locator(".cv-assessment").boundingBox();
  const gateBox = await preview.locator(".a-locked").boundingBox();
  expect(gateBox!.y).toBeGreaterThanOrEqual(gapBox!.y + gapBox!.height);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await preview.screenshot({ path: `tmp/cv-outlook-${test.info().project.name}.png`, style: ".a-site-head { visibility: hidden !important; }" });
  await preview.getByRole("button", { name: "Upload another CV", exact: true }).click();
  await expect(gate).toHaveCount(0);
  expect(await saved()).toBeNull();
  expect(uploads).toBe(1);
});

test("signed-in visitors see an honest error, not a log-in prompt, when the outlook fails", async ({ page }) => {
  await page.goto("/auth/signup?next=/app/onboarding");
  const form = page.locator(".a-auth-form");
  await form.locator('[name="display_name"]').fill("Synthetic Outlook Learner");
  await form.locator('[name="email"]').fill(`outlook-${test.info().project.name}-${Date.now()}@example.test`);
  await form.locator('[name="password"]').fill("synthetic-outlook-password");
  await form.locator('[name="consent"]').check();
  await form.locator('button[type="submit"]').click();
  // Anchored on the path: the signup URL itself carries this destination in its query.
  await expect(page).toHaveURL(/:\d+\/app\/onboarding/);
  await page.route("**/api/preview", async (route) => {
    if (route.request().method() === "PUT") { await route.fulfill({ status: 503, json: { message: "Synthetic failure" } }); return; }
    await route.continue();
  });
  await page.goto("/");
  const preview = page.locator("#start.a-upload");
  await preview.locator('input[type="file"]').setInputFiles({
    name: "synthetic-skills.txt", mimeType: "text/plain", buffer: Buffer.from("SYNTHETIC CV - no personal data\nSkills\nPython; SQL\n"),
  });
  await preview.getByRole("checkbox").check();
  await preview.getByRole("button", { name: "Upload CV", exact: true }).click();
  const rows = preview.locator(".cv-rating-row");
  await expect(rows).toHaveCount(2);
  for (const row of await rows.all()) await row.getByRole("button", { name: "Level 3", exact: true }).click();
  await preview.getByRole("button", { name: "Save and see my skills outlook", exact: true }).click();
  await expect(preview.getByRole("alert")).toContainText("Your ratings are kept");
  await expect(preview.locator(".cv-outlook-gate")).toHaveCount(0);
  await expect(preview.locator('[aria-pressed="true"]')).toHaveCount(2);
});
