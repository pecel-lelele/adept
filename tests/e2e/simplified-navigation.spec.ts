import { expect, test } from "@playwright/test";

test("historical detail sits in one Sources link and the dedicated comparison feature is removed", async ({ page, context, request }) => {
  const api = "http://127.0.0.1:18091";
  const signup = await request.post(`${api}/api/v1/auth/signup`, { data: {
    display_name: "Synthetic UI Reviewer", email: `ui-review-${test.info().project.name}-${Date.now()}@example.test`,
    password: "synthetic-ui-review-password", consent: true,
  } });
  expect(signup.status()).toBe(201);
  const session = await signup.json();
  const headers = { "X-Demo-User": session.token };
  expect((await request.post(`${api}/api/v1/profile/questionnaire`, { headers, data: {
    segment: "working", interests: [], hours_per_week: 6, budget_myr: 300, hrd_eligible: false, learning_style: "mixed",
  } })).ok()).toBe(true);
  expect((await request.put(`${api}/api/v1/profile/skills/confirm`, { headers, data: {
    skills: [{ skill_id: "python", level: 3, source: "confirmed" }, { skill_id: "sql", level: 2, source: "confirmed" }],
  } })).ok()).toBe(true);
  await context.addCookies([{ name: "adept_session", value: session.token, url: "http://127.0.0.1:13091", httpOnly: true, sameSite: "Lax" }]);
  for (const route of ["radar", "matches"]) {
    await page.goto(`/app/${route}`);
    const text = await page.locator("body").innerText();
    expect(text).not.toMatch(/2024-10-(06|12|13|19)|Historical replay:|Historical observations replayed|Frozen offline snapshot exported/);
    await expect(page.getByRole("link", { name: /Compare roles/i })).toHaveCount(0);
    // Attribution is one small link to the consolidated sources; the estimate label and the
    // snapshot date stay in its tooltip and accessible name, not in an expander.
    await expect(page.locator(".a-metabar")).toHaveCount(0);
    const sources = page.locator('.a-sourcelink a[href="/about#data-sources"]').first();
    await expect(sources).toHaveText("Sources");
    await expect(sources).toHaveAttribute("title", /estimates, not facts.*\d{4}-\d{2}-\d{2}/);
    await expect(sources).toHaveAttribute("aria-label", /^Sources\. .*estimates, not facts.*\d{4}-\d{2}-\d{2}/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.screenshot({ path: `tmp/ui-cleanup-${route}-${test.info().project.name}.png` });
  }
  for (const route of ["pathway", "progress"]) {
    await page.goto(`/app/${route}?scenario=fast`);
    await expect(page).toHaveURL(/\/app\/matches\?scenario=fast/);
  }
  expect((await request.get(`${api}/api/v1/pathway/compare`, { headers })).status()).toBe(404);
  const removed = await page.goto("/app/pathway/compare");
  expect(removed?.status()).toBe(404);
});
