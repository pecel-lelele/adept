import { expect, test } from "@playwright/test";

test("radar lists expand and reset, with signed signals and responsive colour modes", async ({ page, context, request }) => {
  const signup = await request.post("http://127.0.0.1:18091/api/v1/auth/signup", { data: {
    display_name: "Synthetic Radar Reviewer", email: `radar-${test.info().project.name}-${Date.now()}@example.test`,
    password: "synthetic-radar-test-password", consent: true,
  } });
  expect(signup.status()).toBe(201);
  const session = await signup.json();
  // Analytics need a saved profile; without one /app/radar redirects to onboarding.
  const headers = { "X-Demo-User": session.token };
  expect((await request.post("http://127.0.0.1:18091/api/v1/profile/questionnaire", { headers, data: {
    segment: "working", interests: [], hours_per_week: 6, budget_myr: 300, hrd_eligible: false, learning_style: "mixed",
  } })).ok()).toBe(true);
  expect((await request.put("http://127.0.0.1:18091/api/v1/profile/skills/confirm", { headers, data: {
    skills: [{ skill_id: "python", level: 3, source: "confirmed" }, { skill_id: "sql", level: 2, source: "confirmed" }],
  } })).ok()).toBe(true);
  await context.addCookies([{ name: "adept_session", value: session.token, url: "http://127.0.0.1:13091", httpOnly: true, sameSite: "Lax" }]);
  await page.goto("/app/radar");
  const skills = page.locator(".radar-skills");
  const rows = skills.locator(".a-row");
  const pager = skills.locator(".a-list-pager");
  const previous = pager.getByRole("button", { name: "Previous", exact: true });
  const next = pager.getByRole("button", { name: "Next", exact: true });
  const status = pager.getByRole("status");
  const pageSize = 10;
  const all = skills.getByRole("radio", { name: /^All / });
  const declining = skills.getByRole("radio", { name: /^Declining/ });
  const total = Number(await all.locator("span").textContent());
  const pages = Math.ceil(total / pageSize);
  expect(pages).toBeGreaterThan(2);
  await expect(rows).toHaveCount(pageSize);
  await expect(previous).toBeDisabled();
  await expect(status).toHaveText(`Page 1 of ${pages}`);
  const firstLabel = await rows.first().locator(".a-row-title").textContent();
  await rows.first().locator("summary").click();
  await expect(skills.locator("details[open]")).toHaveCount(1);
  await next.click();
  await expect(rows).toHaveCount(pageSize);
  await expect(rows.first().locator(".a-row-title")).not.toHaveText(firstLabel ?? "");
  await expect(status).toHaveText(`Page 2 of ${pages}`);
  await expect.poll(async () => (await skills.locator(".a-explorer-tools").boundingBox())?.y ?? 9999).toBeLessThan(160);
  await previous.click();
  await expect(rows.first().locator(".a-row-title")).toHaveText(firstLabel ?? "");
  await expect(skills.locator("details[open]")).toHaveCount(0);
  for (let n = 1; n < pages; n++) await next.click();
  await expect(next).toBeDisabled();
  await expect(status).toHaveText(`Page ${pages} of ${pages}`);
  await expect(rows).toHaveCount(total % pageSize || pageSize);
  const search = skills.getByRole("textbox");
  await search.fill("no-such-synthetic-skill-xyz");
  await expect(rows).toHaveCount(0);
  await expect(skills.locator(".a-row-empty")).toBeVisible();
  await expect(pager).toHaveCount(0);
  await search.fill("");
  await expect(rows).toHaveCount(pageSize);
  await expect(status).toHaveText(`Page 1 of ${pages}`);
  await next.click();
  await declining.click();
  await expect(declining).toHaveAttribute("aria-checked", "true");
  await expect(all).toHaveAttribute("aria-checked", "false");
  if (await pager.count()) await expect(status).toContainText("Page 1 of");
  await expect(skills.locator('.a-signal-track i[data-side="left"]').first()).toBeVisible();
  expect(await skills.locator(".a-row .a-trend").evaluateAll((nodes) => nodes.every((node) => node.getAttribute("data-dir") === "declining"))).toBe(true);
  await all.click();
  await expect(all).toHaveAttribute("aria-checked", "true");
  await expect(rows).toHaveCount(pageSize);
  const groups = page.locator(".radar-role-group");
  await expect(groups).toHaveCount(3);
  const thin = page.locator('[data-direction="insufficient"]');
  await expect(thin.locator(".a-trend")).toHaveCount(0);
  const togglePositions = async () => Promise.all((await page.locator(".radar-role-toggle").all()).map(async (button) => (await button.boundingBox())?.y ?? -1));
  const assertAligned = async () => {
    if (test.info().project.name === "desktop") {
      await expect.poll(async () => { const ys = await togglePositions(); return Math.max(...ys) - Math.min(...ys); }).toBeLessThan(2);
    }
  };
  await assertAligned();
  for (const group of await groups.all()) {
    const count = Number(await group.locator(".radar-count").textContent());
    await expect(group.getByRole("link")).toHaveCount(Math.min(5, count));
    if (count > 5) {
      const toggle = group.getByRole("button", { name: `View all ${count}`, exact: true });
      await expect(group.locator(".radar-role-preview")).toHaveCount(1);
      await expect(group.locator(".radar-role-extra")).toHaveAttribute("inert", "");
      const firstRow = await group.getByRole("link").first().elementHandle();
      await toggle.click();
      await expect(group.getByRole("link")).toHaveCount(count);
      expect(await firstRow?.isVisible()).toBeTruthy();
      await assertAligned();
      await group.getByRole("button", { name: "Show less", exact: true }).click();
      await expect(group.getByRole("link")).toHaveCount(5);
      await expect(group.locator(".radar-role-toggle")).toHaveAttribute("aria-expanded", "false");
    } else await expect(group.locator(".radar-role-toggle")).toHaveCount(0);
  }
  const columnCount = () => page.locator(".radar-role-columns").evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(" ").length);
  expect(await columnCount()).toBe(test.info().project.name === "desktop" ? 3 : 1);
  if (test.info().project.name === "desktop") {
    const viewport = page.viewportSize();
    await page.setViewportSize({ width: 900, height: 900 });
    expect(await columnCount()).toBe(2);
    if (viewport) await page.setViewportSize(viewport);
  }
  const labour = page.locator(".labour-context");
  await expect(labour.getByRole("heading", { name: "Malaysian labour context", exact: true })).toBeVisible();
  await expect(labour.locator(".labour-stat")).toHaveCount(3);
  await expect(labour.locator("dd")).toHaveText(["2.9%", "71%", "68.9%"]);
  await expect(labour.getByLabel("Month", { exact: true })).toBeDisabled();
  // Attribution is the same single Sources link; the snapshot date sits in its accessible name.
  const labourSources = labour.locator('.a-sourcelink a[href="/about#data-sources"]');
  await expect(labourSources).toHaveCount(1);
  await expect(labourSources).toHaveAttribute("aria-label", /^Sources\. .*\d{4}-\d{2}-\d{2}/);
  expect(await labour.locator(".labour-stats").evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(" ").length)).toBe(test.info().project.name === "desktop" ? 3 : 1);
  // The app has one light theme: a dark OS preference must not turn only these cards dark.
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
    await expect(page.locator(".radar-role-directions")).toHaveCSS("background-color", "rgb(255, 255, 255)");
    await expect(page.locator(".radar-skills-card h2")).toHaveCSS("color", "rgb(24, 35, 28)");
    await page.locator(".radar-role-directions").screenshot({ path: `tmp/playwright-results/radar-roles-${test.info().project.name}-${colorScheme}.png` });
    await page.locator(".radar-skills-card").screenshot({ path: `tmp/playwright-results/radar-skills-${test.info().project.name}-${colorScheme}.png` });
    await labour.screenshot({ path: `tmp/playwright-results/radar-labour-${test.info().project.name}-${colorScheme}.png` });
  }
});
