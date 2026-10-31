import { expect, test } from "@playwright/test";

test("radar lists expand and reset, with signed signals and responsive colour modes", async ({ page, context, request }) => {
  const signup = await request.post("http://127.0.0.1:18091/api/v1/auth/signup", { data: {
    display_name: "Synthetic Radar Reviewer", email: `radar-${test.info().project.name}-${Date.now()}@example.test`,
    password: "synthetic-radar-test-password", consent: true,
  } });
  expect(signup.status()).toBe(201);
  const session = await signup.json();
  await context.addCookies([{ name: "adept_session", value: session.token, url: "http://127.0.0.1:13091", httpOnly: true, sameSite: "Lax" }]);
  await page.goto("/app/radar");
  const skills = page.locator(".radar-skills");
  const rows = skills.locator(".a-row");
  const previous = skills.getByRole("button", { name: "Previous page", exact: true });
  const next = skills.getByRole("button", { name: "Next page", exact: true });
  const total = Number(await skills.getByRole("button", { name: /^All / }).locator("span").textContent());
  const pages = Math.ceil(total / 15);
  await expect(rows).toHaveCount(15);
  await expect(previous).toBeDisabled();
  await expect(skills.locator(".radar-pagination")).toContainText(`Page 1 of ${pages}`);
  const firstLabel = await rows.first().locator(".a-row-title").textContent();
  await rows.first().locator("summary").click();
  await expect(skills.locator("details[open]")).toHaveCount(1);
  await next.click();
  await expect(rows).toHaveCount(15);
  await expect(rows.first().locator(".a-row-title")).not.toHaveText(firstLabel ?? "");
  await expect(skills.locator(".radar-pagination")).toContainText(`Page 2 of ${pages}`);
  await expect.poll(async () => (await skills.locator(".a-explorer-tools").boundingBox())?.y ?? 9999).toBeLessThan(160);
  await previous.click();
  await expect(rows.first().locator(".a-row-title")).toHaveText(firstLabel ?? "");
  await expect(skills.locator("details[open]")).toHaveCount(0);
  for (let n = 1; n < pages; n++) await next.click();
  await expect(next).toBeDisabled();
  await expect(rows).toHaveCount(total % 15 || 15);
  await expect(skills.locator(".radar-pagination")).toContainText(`${total} skills`);
  const search = skills.getByRole("textbox");
  await search.fill("no-such-synthetic-skill-xyz");
  await expect(rows).toHaveCount(0);
  await expect(previous).toBeDisabled();
  await expect(next).toBeDisabled();
  await expect(skills.locator(".radar-pagination")).toContainText("Page 1 of 1");
  await search.fill("");
  await expect(rows).toHaveCount(15);
  await next.click();
  await skills.getByRole("button", { name: /^Declining/ }).click();
  await expect(previous).toBeDisabled();
  await expect(skills.getByRole("button", { name: /^Declining/ })).toHaveAttribute("aria-pressed", "true");
  await expect(skills.locator('.a-signal-track i[data-side="left"]').first()).toBeVisible();
  await skills.getByRole("button", { name: /^All / }).click();
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
  await expect(labour.locator(".labour-snapshot")).toHaveText("Showing last good snapshot from 2026-08-01");
  await labour.locator(".labour-sources summary").click();
  await expect(labour.getByRole("link", { name: /Department of Statistics Malaysia/ })).toHaveAttribute("href", "https://open.dosm.gov.my/data-catalogue/lfs_month");
  await expect(labour.locator(".labour-sources")).toContainText("Retrieved 2026-10-30");
  await labour.locator(".labour-sources summary").click();
  expect(await labour.locator(".labour-stats").evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(" ").length)).toBe(test.info().project.name === "desktop" ? 3 : 1);
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
    await expect(page.locator(".radar-role-directions")).toHaveCSS("background-color", colorScheme === "dark" ? "rgb(24, 35, 30)" : "rgb(255, 255, 255)");
    await expect(page.locator(".radar-skills-card h2")).toHaveCSS("color", colorScheme === "dark" ? "rgb(237, 244, 238)" : "rgb(24, 35, 28)");
    await page.locator(".radar-role-directions").screenshot({ path: `tmp/playwright-results/radar-roles-${test.info().project.name}-${colorScheme}.png` });
    await page.locator(".radar-skills-card").screenshot({ path: `tmp/playwright-results/radar-skills-${test.info().project.name}-${colorScheme}.png` });
    await labour.screenshot({ path: `tmp/playwright-results/radar-labour-${test.info().project.name}-${colorScheme}.png` });
  }
});
