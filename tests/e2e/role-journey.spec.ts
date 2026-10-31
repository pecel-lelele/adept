import { expect, test, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";

const api = "http://127.0.0.1:18091";
const web = "http://127.0.0.1:13091";

async function signup(request: APIRequestContext, suffix: string, extra: Record<string, unknown> = {}) {
  const response = await request.post(`${api}/api/v1/auth/signup`, { data: {
    display_name: "Synthetic Journey Reviewer", email: `journey-${suffix}-${Date.now()}@example.test`,
    password: "synthetic-journey-password", consent: true, ...extra,
  } });
  expect(response.status()).toBe(201);
  return response.json() as Promise<{ token: string; account: { id: string; org_id: string } }>;
}

async function profile(request: APIRequestContext, token: string) {
  const headers = { "X-Demo-User": token, "X-Workspace": "personal" };
  expect((await request.post(`${api}/api/v1/profile/questionnaire`, { headers, data: {
    segment: "working", interests: [], hours_per_week: 6, budget_myr: 300, hrd_eligible: false, learning_style: "mixed",
  } })).ok()).toBe(true);
  expect((await request.put(`${api}/api/v1/profile/skills/confirm`, { headers, data: {
    skills: [{ skill_id: "python", level: 1, source: "confirmed" }, { skill_id: "sql", level: 1, source: "confirmed" }],
  } })).ok()).toBe(true);
}

/** "Mark done" is proof-gated: it reveals a certificate-link field, and saving the link completes the course. */
async function markFirstCourseDone(page: Page) {
  await page.getByRole("button", { name: "Mark done", exact: true }).first().click();
  // A synthetic non-provider link: the API records it as not yet verified without any network call.
  await page.locator('input[type="url"]').fill("https://example.test/synthetic-certificate");
  await page.getByRole("button", { name: "Add certificate link", exact: true }).click();
}

async function session(context: BrowserContext, token: string, org?: string) {
  await context.addCookies([
    { name: "adept_session", value: token, url: web, httpOnly: true, sameSite: "Lax" },
    ...(org ? [{ name: "adept_org", value: org, url: web, httpOnly: true, sameSite: "Lax" as const }] : []),
  ]);
}

test("personal locks, explicit choice, course completion and role switching", async ({ page, context, request }, info) => {
  const user = await signup(request, `personal-${info.project.name}`);
  await profile(request, user.token);
  await session(context, user.token);
  await page.goto("/app/matches?scenario=fast");
  await expect(page.getByRole("button", { name: "Choose this role", exact: true }).first()).toBeVisible();
  const nav = page.locator(info.project.name === "mobile" ? ".a-tabs" : ".a-sidenav");
  await expect(nav.locator('[data-locked="true"]').first()).toBeVisible();
  await nav.getByRole("link", { name: /^Plan/ }).click();
  await expect(page).toHaveURL(/\/app\/matches\?choose_role=1&scenario=fast/);
  await expect(page.getByText("Choose a target role first.", { exact: true })).toBeVisible();
  if (info.project.name === "mobile") {
    await page.getByRole("button", { name: "More", exact: true }).click();
    await page.getByRole("dialog").getByRole("link", { name: /^Progress/ }).click();
  } else {
    await nav.getByRole("link", { name: /^Progress/ }).click();
  }
  await expect(page).toHaveURL(/choose_role=1/);
  const card = page.locator(".a-rolecard").first();
  const role = await card.locator('input[name="role_id"]').inputValue();
  await card.getByRole("button", { name: "Choose this role", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/app/pathway\\?role=${role}&scenario=fast`), { timeout: 40000 });
  await expect(page.locator('footer[aria-label="Plan summary"]')).toContainText("RM");
  await expect(page.locator('[data-locked="true"]')).toHaveCount(0);
  await page.goto(`/app/progress?role=${role}&scenario=fast`);
  const bar = page.getByRole("progressbar");
  const before = Number(await bar.getAttribute("aria-valuenow"));
  await markFirstCourseDone(page);
  await expect.poll(async () => Number(await bar.getAttribute("aria-valuenow"))).toBeGreaterThan(before);
  await expect(page.getByText("Estimated skill fit", { exact: true })).toBeVisible();
  const headers = { "X-Demo-User": user.token, "X-Workspace": "personal" };
  const progress = await (await request.get(`${api}/api/v1/pathway/progress`, { headers, params: { role_id: role, scenario: "fast" } })).json();
  await page.goto("/app/matches?scenario=fast");
  await expect(page.getByRole("link", { name: "Open plan", exact: true })).toHaveCount(1);
  await page.locator(".a-rolecard").nth(1).getByRole("button", { name: "Choose this role", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/pathway\?role=/);
  await page.goto(`/app/progress?role=${role}&scenario=fast`);
  await expect(page.getByRole("button", { name: "Undo", exact: true }).first()).toBeVisible();
  const retained = await (await request.get(`${api}/api/v1/pathway/progress`, { headers, params: { role_id: role, scenario: "fast" } })).json();
  expect(retained.course_status).toEqual(progress.course_status);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: `tmp/role-journey-personal-${info.project.name}.png`, fullPage: true });
});

test("team assignment, proposed role, acceptance and consent-aware team progress", async ({ page, context, request }, info) => {
  const manager = await signup(request, `manager-${info.project.name}`, {
    workspace: "organisation", organisation: { type: "company", name: "Synthetic GBS Team", industry: "Synthetic review", size: 3 },
  });
  const org = manager.account.org_id;
  const hr = { "X-Demo-User": manager.token, "X-Workspace": org };
  const details = await (await request.get(`${api}/api/v1/org/me`, { headers: hr })).json();
  const members = [];
  for (let n = 0; n < 3; n++) {
    const member = await signup(request, `member-${n}-${info.project.name}`, { join_code: details.join_code, share_skills: true });
    await profile(request, member.token);
    members.push(member);
  }
  const brief = {
    title: "Synthetic GBS learning programme", objectives: ["data_driven"],
    roles: [{ role_id: "data-analyst", headcount: 3 }], member_ids: members.map((m) => m.account.id),
    target_date: "2027-01-31", hours_per_week: 6, budget_total_myr: 900, budget_per_member_myr: 300,
  };
  const generated = await request.post(`${api}/api/v1/org/programmes/generate`, { headers: hr, data: brief });
  expect(generated.ok()).toBe(true);
  const proposal = await generated.json();
  const sent = await request.post(`${api}/api/v1/org/programmes`, { headers: hr, data: { brief, token: proposal.token } });
  expect(sent.status()).toBe(201);
  const programme = await sent.json();
  const pid = programme.record.id;
  const member = members[0]!;
  await session(context, member.token, org);
  await page.goto("/work/plan");
  await expect(page.getByText(`Assigned by your team · Synthetic GBS Team`, { exact: true })).toBeVisible();
  await page.getByText("Propose a different role", { exact: true }).click();
  const alternativeLabel = await page.locator('select[name="proposed_role_id"] option[value="business-analyst"]').textContent();
  await page.locator('select[name="proposed_role_id"]').selectOption("business-analyst");
  await page.locator('form:has(select[name="proposed_role_id"])').getByRole("button").click();
  await expect(page.getByText(`Proposed role: ${alternativeLabel}`, { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(page.getByRole("link", { name: "Programme progress", exact: true })).toBeVisible();
  for (const peer of members.slice(1)) {
    const accepted = await request.post(`${api}/api/v1/org/programmes/${pid}/decision`, { headers: { "X-Demo-User": peer.token, "X-Workspace": org }, data: { decision: "accept" } });
    expect(accepted.ok()).toBe(true);
  }
  await page.getByRole("link", { name: "Programme progress", exact: true }).click();
  await markFirstCourseDone(page);
  await expect(page.getByRole("button", { name: "Undo", exact: true }).first()).toBeVisible();
  await session(context, manager.token, org);
  await page.goto("/org/gaps");
  await expect(page.getByRole("heading", { name: "Team learning progress", exact: true })).toBeVisible();
  const counts = await (await request.get(`${api}/api/v1/org/gaps`, { headers: hr })).json();
  expect(counts.learning_progress.some((row: { completed_courses: number | null }) => (row.completed_courses ?? 0) > 0)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: `tmp/role-journey-team-${info.project.name}.png`, fullPage: true });
  expect((await request.put(`${api}/api/v1/org/me/sharing`, { headers: { "X-Demo-User": member.token, "X-Workspace": org }, data: { share_skills: false } })).ok()).toBe(true);
  await page.reload();
  await expect(page.getByText("Too few sharing members for this skill", { exact: true }).first()).toBeVisible();
  const hidden = await (await request.get(`${api}/api/v1/org/gaps`, { headers: hr })).json();
  expect(hidden.learning_progress.every((row: { suppressed: boolean; completed_courses: number | null }) => row.suppressed && row.completed_courses === null)).toBe(true);
});
