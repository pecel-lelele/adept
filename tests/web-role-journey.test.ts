import assert from "node:assert/strict";
import test from "node:test";

import * as navigation from "../src/web/src/config/navigation.ts";
import * as journeys from "../src/web/src/lib/navigation.ts";
import * as scenarios from "../src/web/src/lib/scenario.ts";
import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

const link = { default: ({ children, ...props }) => React.createElement("a", props, children) };

test("desktop and mobile show clickable locks until an explicit personal target is saved", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const intl = translations(locale);
    const { SideNav, TabBar } = loadComponent("src/components/shell/Nav.tsx", {
      "next-intl": intl, "next/link": link,
      "next/navigation": { usePathname: () => "/app", useSearchParams: () => new URLSearchParams("scenario=fast") },
      "@/config/navigation": navigation, "@/lib/navigation": journeys,
    });
    for (const component of [SideNav, TabBar]) {
      const locked = renderToStaticMarkup(React.createElement(component, { ws: navigation.learnerWorkspace, roleChosen: false, doneSteps: [], tools: null }));
      assert.match(locked, /data-locked="true"/);
      assert.match(locked, /href="\/app\/matches\?choose_role=1&amp;scenario=fast"/);
      assert.ok(locked.includes(intl.useTranslations("ui.nav")("chooseRoleFirst")));
      const chosen = renderToStaticMarkup(React.createElement(component, { ws: navigation.learnerWorkspace, roleChosen: true, doneSteps: [1, 2, 3], tools: null }));
      assert.doesNotMatch(chosen, /data-locked="true"/);
      const work = renderToStaticMarkup(React.createElement(component, { ws: navigation.workWorkspace, roleChosen: false, doneSteps: [], tools: null }));
      assert.doesNotMatch(work, /data-locked="true"/);
    }
  }
});

test("a URL role cannot unlock Plan or Progress without a saved choice", async () => {
  for (const route of ["pathway", "progress"]) {
    let target = "";
    const { default: Page } = loadComponent(`src/app/app/${route}/page.tsx`, {
      "@/components": { ErrorState: () => null },
      "@/features/pathway": { fetchPlanStatus: async () => ({ ok: true, data: { saved: null } }) },
      "@/lib/scenario": scenarios,
      "next/navigation": { redirect: (url) => { target = url; throw new Error("Redirect"); } },
    });
    await assert.rejects(() => Page({ searchParams: Promise.resolve({ scenario: "fast", role: "data-analyst" }) }), /Redirect/);
    assert.equal(target, "/app/matches?scenario=fast&choose_role=1");
  }
});

test("a failed plan check reports the error instead of asking the learner to choose again", async () => {
  for (const route of ["pathway", "progress"]) {
    const { default: Page } = loadComponent(`src/app/app/${route}/page.tsx`, {
      "@/components": { ErrorState: () => React.createElement("section", { "data-error": true }) },
      "@/features/pathway": { fetchPlanStatus: async () => ({ ok: false, status: 503, code: "server_error", message: "synthetic failure" }) },
      "@/lib/scenario": scenarios,
      "next/navigation": { redirect: () => { throw new Error("Must not redirect on a failed check"); } },
    });
    const html = renderToStaticMarkup(await Page({ searchParams: Promise.resolve({ scenario: "fast" }) }));
    assert.match(html, /data-error/);
  }
});

test("an API-reported untracked role sends the learner to choose it", async () => {
  let target = "";
  const intl = translations("en");
  const { ProgressView } = loadComponent("src/features/pathway/components/ProgressView.tsx", {
    "next-intl/server": { getTranslations: async (ns) => intl.useTranslations(ns) },
    "next/navigation": { redirect: (url) => { target = url; throw new Error("Redirect"); } },
    "@/components": { ErrorState: () => null, Kpis: () => null, MetaBar: () => null, PageHeader: () => null },
    "@/config/navigation": navigation,
    "../actions": {}, "./ActionForm": {}, "./EvidenceBadge": {}, "./EvidenceForm": {},
    "../api": { fetchProgress: async () => ({ ok: true, data: { trackable: false } }) },
  });
  await assert.rejects(() => ProgressView({ roleId: "synthetic-role", scenario: "fast" }), /Redirect/);
  assert.equal(target, "/app/matches?scenario=fast&choose_role=1");
});

test("the current target replaces the choose button so re-plan review is not bypassed", async () => {
  const nothing = () => null;
  const intl = translations("en");
  const t = intl.useTranslations("matching");
  const m = { role_id: "synthetic/role", label: "Synthetic role", score: 0.8, meta: {}, components: [], missing_skills: [], partial_skills: [], sdg_targets: [] };
  for (const saved of [null, { role_id: "synthetic/role", scenario: "moderate" }, { role_id: "synthetic/other", scenario: "moderate" }]) {
    const { MatchDetailView } = loadComponent("src/features/matching/components/MatchDetailView.tsx", {
      "next-intl": intl,
      "next-intl/server": { getTranslations: async (ns) => intl.useTranslations(ns) },
      "next/link": link,
      "@/components": {
        EstimateLabel: nothing, MetaBar: nothing, ScoreBreakdown: nothing,
        PageHeader: ({ actions, children }) => React.createElement("header", {}, actions, children),
      },
      "@/components/ErrorState": { ErrorState: nothing },
      "@/components/HistoricalSnapshotBanner": { HistoricalSnapshotBanner: nothing },
      "@/components/viz": { scoreColour: () => "inherit" },
      "@/config/navigation": navigation,
      "@/features/jobs": { RoleOpeningsCard: nothing },
      "@/features/scenarios/components/RoleOutlookPanel": { RoleOutlookPanel: nothing },
      "@/features/pathway/api": { fetchPlanStatus: async () => ({ ok: true, data: { saved } }) },
      "@/features/pathway/actions": { savePlanAction: nothing },
      "@/features/pathway/components/ActionForm": { ActionForm: ({ label }) => React.createElement("button", {}, label) },
      "../api": { fetchMatch: async () => ({ ok: true, data: m }) },
      "./labels": { componentLabels: async () => ({}) },
      "./MatchImprovements": { MatchImprovements: nothing }, "./MatchSdgTargets": { MatchSdgTargets: nothing },
      "./ProfileNote": { ProfileNote: nothing }, "./CriticalOccupationBadge": { CriticalOccupationBadge: nothing },
    });
    const html = renderToStaticMarkup(await resolveTree(await MatchDetailView({ roleId: m.role_id, scenario: "fast" })));
    const isTarget = saved?.role_id === m.role_id;
    assert.equal(html.includes(t("chooseRole")), !isTarget);
    assert.equal(html.includes(t("openPlan")), isTarget);
    if (isTarget) assert.match(html, /href="\/app\/pathway\?role=synthetic%2Frole&amp;scenario=moderate"/);
  }
});

test("a programme link for an ineligible member selects nobody instead of the whole team", () => {
  const { initialMemberSelection } = loadComponent("src/features/org/programmes/components/ProgrammeWizard.tsx", {
    "next-intl": translations("en"), "../actions": {},
    "@/lib/api/error-message": { errorMessage: () => "" },
    "@/components/Kpis": { Kpis: () => null }, "@/components/MetaBar": { MetaBar: () => null },
  });
  const members = [{ user_id: "synthetic-a" }, { user_id: "synthetic-b" }];
  assert.deepEqual([...initialMemberSelection(members, "synthetic-a")], ["synthetic-a"]);
  assert.deepEqual([...initialMemberSelection(members, "stopped-sharing")], []);
  assert.deepEqual([...initialMemberSelection(members, undefined)], ["synthetic-a", "synthetic-b"]);
  for (const locale of ["en", "ms", "zh"]) assert.ok(translations(locale).useTranslations("org.programmes")("memberNotEligible"));
});

test("choosing a role pins the personal workspace and redirects only after the server saves it", async () => {
  let workspace;
  let submitted;
  let redirectTo = "";
  let accepted = false;
  const { savePlanAction } = loadComponent("src/features/pathway/actions.ts", {
    "next/cache": { revalidatePath: () => {} },
    "next/navigation": { redirect: (url) => { redirectTo = url; throw new Error("Redirect"); } },
    "@/lib/api": { getApi: async (options) => { workspace = options.workspace; return { POST: async (path, input) => {
      submitted = { path, ...input };
      return { response: new Response(null, { status: accepted ? 200 : 503 }) };
    } }; } },
    "@/lib/auth/workspace": { PERSONAL: "personal", isOrgId: () => true },
    "@/lib/scenario": scenarios,
    "./action-state": { actionError: () => "server_error" },
  });
  const form = new FormData();
  form.set("role_id", "data-analyst"); form.set("scenario", "fast");
  const failed = await savePlanAction({}, form);
  assert.equal(failed.error, "server_error");
  assert.equal(redirectTo, "");
  accepted = true;
  await assert.rejects(() => savePlanAction({}, form), /Redirect/);
  assert.equal(workspace, "personal");
  assert.equal(submitted.body.role_id, "data-analyst");
  assert.equal(submitted.body.scenario, "fast");
  assert.equal(redirectTo, "/app/pathway?role=data-analyst&scenario=fast");
});
