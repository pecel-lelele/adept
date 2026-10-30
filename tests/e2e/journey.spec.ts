import { expect, test } from "@playwright/test";
import { resolve } from "node:path";

const api = "http://127.0.0.1:18091";

test("public trust pages are reachable and fit the viewport", async ({ page }) => {
  for (const path of ["/privacy", "/terms", "/faq", "/about"]) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
  }
  await page.screenshot({ path: `tmp/playwright-results/public-${test.info().project.name}.png`, fullPage: true });
});

test("synthetic CV reaches radar, an explained match and a saved sourced plan", async ({ page, context, request }) => {
  const signup = await request.post(`${api}/api/v1/auth/signup`, { data: {
    display_name: "Synthetic Browser Learner", email: `synthetic-${test.info().project.name}-${Date.now()}@example.test`,
    password: "synthetic-browser-test-password", consent: true,
  } });
  expect(signup.status()).toBe(201);
  const session = await signup.json();
  await context.addCookies([{ name: "adept_session", value: session.token, url: "http://127.0.0.1:13091", httpOnly: true, sameSite: "Lax" }]);
  await page.goto("/app/onboarding");
  for (let n = 0; n < 3; n++) await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.locator('input[type="file"]').setInputFiles(resolve("docs/demo-cvs/cv_sofia_tan_process_automation_analyst.pdf"));
  await expect(page.locator(".a-skillpick").first()).toBeVisible({ timeout: 20000 });
  await page.getByRole("button", { name: "Save and see my skills outlook", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/radar/);
  await expect(page.getByText(/snapshot|data as of|showing.*snapshot/i).first()).toBeVisible();
  await page.goto("/app/matches");
  const detail = page.locator('a[href^="/app/matches/"]').first();
  await expect(detail).toBeVisible();
  await detail.click();
  await expect(page.getByText(/skills to build|score|match/i).first()).toBeVisible();
  await page.locator('main a[href^="/app/pathway?role="]').first().click();
  await page.getByRole("button", { name: "Choose this role and save the plan", exact: true }).click();
  await expect(page.getByText(/Saved as your plan/)).toBeVisible();
  await expect(page.locator('.a-course-row[href^="https://learn.microsoft.com"]').first()).toBeVisible();
  const saved = await request.get(`${api}/api/v1/pathway/plans/me`, { headers: { "X-Demo-User": session.token } });
  expect(saved.ok()).toBeTruthy(); expect((await saved.json()).saved?.role_id).toBeTruthy();
  await page.screenshot({ path: `tmp/playwright-results/plan-${test.info().project.name}.png`, fullPage: true });
});

test("team CTAs and deep workspace links match signed-out, manager and member sessions", async ({ page, context, request }) => {
  await page.goto("/?for=teams");
  await expect(page.getByRole("link", { name: "Set up your team, free", exact: true }).first()).toHaveAttribute("href", "/auth/signup?mode=organisation");
  const managerSignup = await request.post(`${api}/api/v1/auth/signup`, { data: {
    display_name: "Synthetic Browser Manager", email: `synthetic-manager-${test.info().project.name}-${Date.now()}@example.test`,
    password: "synthetic-browser-test-password", consent: true, workspace: "organisation",
    organisation: { type: "company", name: "Synthetic Browser Team", industry: "Synthetic testing", size: 2 },
  } });
  expect(managerSignup.status()).toBe(201);
  const manager = await managerSignup.json();
  const signIn = async (token: string) => {
    await context.clearCookies();
    await context.addCookies([{ name: "adept_session", value: token, url: "http://127.0.0.1:13091", httpOnly: true, sameSite: "Lax" }]);
  };
  await signIn(manager.token);
  await page.goto("/?for=teams");
  await expect(page.getByRole("link", { name: "Open team workspace", exact: true }).first()).toHaveAttribute("href", "/org");
  await page.goto("/org/members?scenario=fast");
  await expect(page.locator("main h1")).toBeVisible();
  await expect(page).toHaveURL(/\/org\/members\?scenario=fast$/);
  const org = await request.get(`${api}/api/v1/org/me`, { headers: { "X-Demo-User": manager.token, "X-Workspace": manager.account.org_id } });
  expect(org.ok()).toBeTruthy();
  const memberSignup = await request.post(`${api}/api/v1/auth/signup`, { data: {
    display_name: "Synthetic Browser Member", email: `synthetic-member-${test.info().project.name}-${Date.now()}@example.test`,
    password: "synthetic-browser-test-password", consent: true, join_code: (await org.json()).join_code, share_skills: false,
  } });
  expect(memberSignup.status()).toBe(201);
  const member = await memberSignup.json();
  await signIn(member.token);
  await page.goto("/?for=teams");
  await expect(page.getByRole("button", { name: "Create a team account", exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Join your team with a code", exact: true }).first()).toHaveAttribute("href", "/app/join");
  await page.goto("/work/progress?scenario=fast");
  await expect(page.locator("main h1")).toBeVisible();
  await expect(page).toHaveURL(/\/work\/progress\?scenario=fast$/);
  expect((await page.request.get("/api/workspace?to=personal")).status()).toBe(405);
  await page.goto("/about");
  await expect(page.locator('.a-site-actions a[href="/work"]').first()).toBeVisible();
});
