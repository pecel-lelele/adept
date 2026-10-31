import assert from "node:assert/strict";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import test from "node:test";

import * as navigation from "../src/web/src/config/navigation.ts";
import * as draft from "../src/web/src/features/profile/intake-draft.ts";
import * as skillSearch from "../src/web/src/features/profile/skill-search.ts";
import * as i18n from "../src/web/src/lib/i18n/config.ts";
import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

const nothing = () => null;
const failure = { ok: false, code: "network", status: 0 };
const link = { default: ({ children, prefetch: _prefetch, ...props }) => React.createElement("a", props, children) };
const { PageHeader } = loadComponent("src/components/PageHeader.tsx");
const { Fold } = loadComponent("src/components/Fold.tsx");
const { RouteErrorState } = loadComponent("src/features/core/components/RouteErrorState.tsx", { "next/link": link });

function fixtures(locale: string) {
  const intl = translations(locale);
  const { EstimateLabel } = loadComponent("src/components/EstimateLabel.tsx", { "next-intl": intl });
  const ErrorState = () => React.createElement("section", { "data-error": true }, intl.useTranslations("ui.error")("title"));
  return {
    "next-intl": intl,
    "next-intl/server": { getTranslations: async (ns: string) => intl.useTranslations(ns) },
    "next/link": link,
    "@/components": { PageHeader, EstimateLabel, ErrorState, MetaBar: nothing, Kpis: nothing, TrendPill: nothing },
    "@/components/ErrorState": { ErrorState },
    "@/components/Fold": { Fold },
    "@/components/HistoricalSnapshotBanner": { HistoricalSnapshotBanner: nothing },
    "@/config/navigation": navigation,
    "@/components/viz": { scoreColour: () => "inherit" },
    "@/features/jobs": { fetchJobsSummary: async () => failure },
    "@/features/profile/api": { fetchMyProfile: async () => failure },
    "@/features/trends/api": { fetchRadar: async () => { throw new Error("No separate radar read"); } },
    "@/features/core/components/AccountDataCard": { AccountDataCard: nothing },
    "@/lib/auth/workspaces": { getWorkspaceResult: async () => failure },
    "@/features/scenarios/components/RoleOutlookPanel": { RoleOutlookPanel: nothing },
    "./labels": { componentLabels: async () => ({}) },
    "./ReplayChanges": { ReplayChanges: nothing }, "./SdgWeightSlider": { SdgWeightSlider: nothing },
    "./MatchImprovements": { MatchImprovements: nothing }, "./ScenarioDelta": { ScenarioDelta: nothing },
    "./MatchSdgTargets": { MatchSdgTargets: nothing }, "./ProfileNote": { ProfileNote: nothing },
    "./CriticalOccupationBadge": { CriticalOccupationBadge: nothing }, "./PathwaySteps": { PathwaySteps: nothing },
    "./ActionForm": { ActionForm: nothing }, "../actions": {},
    "./SignalExplorer": { SignalExplorer: nothing }, "./RoleDirectionsCard": { RoleDirectionsCard: nothing },
    "./TrendRangeCard": { TrendRangeCard: nothing },
    "../range": loadComponent("src/features/trends/range.ts"),
    "@/components/DataAsOf": { DataAsOf: nothing }, "@/lib/auth/account": { getAccount: async () => null },
  };
}

test("failed journey screens keep their translated heading, stage and scenario before the error", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const common = fixtures(locale);
    const cases = [
      ["trends/components/RadarView", "RadarView", 2, { fetchRadar: async () => failure, fetchCompare: async () => failure }],
      ["profile/components/ProfileView", "ProfileView", 1, { fetchMyProfile: async () => failure, fetchSkillCatalogue: async () => failure }],
      ["pathway/components/PathwayView", "PathwayView", 4, { fetchPathway: async () => failure, fetchPlanStatus: async () => failure }],
      ["matching/components/MatchDetailView", "MatchDetailView", 3, { fetchMatch: async () => failure, fetchMatches: async () => failure }],
    ] as const;
    for (const [path, name, step, api] of cases) {
      const component = loadComponent(`src/features/${path}.tsx`, { ...common, "../api": api, "@/features/trends/api": { fetchRadar: async () => failure } })[name];
      const html = renderToStaticMarkup(await resolveTree(await component({ scenario: "fast", roleId: "synthetic", snapshotDate: "2026-10-13" })));
      assert.ok(html.indexOf("<h1") < html.indexOf("data-error"));
      assert.ok(html.includes(translations(locale).useTranslations("ui.page")("stepOf", { step: String(step), total: "6" })));
      assert.ok(html.includes(translations(locale).useTranslations("common.scenario")("fast")));
      assert.doesNotMatch(html, /undefined/);
    }
  }
});

test("matches keep their own snapshot picker and only the three highest ranks are expanded", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const matches = Array.from({ length: 6 }, (_, index) => ({
      role_id: `synthetic/${index}`, label: `Synthetic role ${index}`, score: 0.9 - index / 10,
      components: [{ name: "skill_overlap", weight: 1, value: index % 2 ? 0.3 : 0.7, provided: true, explanation: "Synthetic score" }],
      missing_skills: [], partial_skills: [], sdg_targets: [],
    }));
    const dates = ["2026-10-13", "2026-10-20"];
    const { MatchesView } = loadComponent("src/features/matching/components/MatchesView.tsx", {
      ...fixtures(locale),
      "../api": { fetchMatches: async () => ({ ok: true, data: { matches, meta: { available_snapshots: dates } } }) },
      "./SnapshotPicker": { SnapshotPicker: ({ dates }) => React.createElement("select", {}, dates.map((d: string) => React.createElement("option", { key: d }, d))) },
    });
    const html = renderToStaticMarkup(await resolveTree(await MatchesView({ scenario: "fast" })));
    assert.ok(html.includes(dates[0]) && html.includes(dates[1]));
    assert.equal((html.match(/<details/g) ?? []).length, 3);
    assert.doesNotMatch(html, /<details[^>]*open/);
    assert.equal((html.match(/class="a-card a-rolecard"/g) ?? []).length, matches.length);
    for (const index of [3, 4, 5]) assert.match(html, new RegExp(`<summary[\\s\\S]*?${index + 1}\\. Synthetic role ${index}`));
    assert.match(html, /matches\/synthetic%2F0/);
    if (process.env.WEB_UX_PROOF_DIR) {
      mkdirSync(process.env.WEB_UX_PROOF_DIR, { recursive: true });
      writeFileSync(`${process.env.WEB_UX_PROOF_DIR}/06-matches-${locale}.html`, html);
    }
  }
});

test("snapshot selection replaces history and preserves scenario and ranking filters", () => {
  const targets: string[] = [];
  const { SnapshotPicker } = loadComponent("src/features/matching/components/SnapshotPicker.tsx", {
    react: { useTransition: () => [false, (fn) => fn()] },
    "@/components/useBusy": { useBusy: nothing },
    "next/navigation": {
      useRouter: () => ({ replace: (url: string) => targets.push(url), push: () => assert.fail("Must replace") }),
      usePathname: () => "/app/matches", useSearchParams: () => new URLSearchParams("scenario=fast&sdg=0.25&snapshot_date=old"),
    },
  });
  const tree = SnapshotPicker({ dates: [], value: "", label: "Snapshot", latestLabel: "Latest" });
  const select = tree.props.children[1];
  select.props.onChange({ target: { value: "2026-10-13" } });
  select.props.onChange({ target: { value: "" } });
  assert.equal(targets[0], "/app/matches?scenario=fast&sdg=0.25&snapshot_date=2026-10-13");
  assert.equal(targets[1], "/app/matches?scenario=fast&sdg=0.25");
});

test("comparison's best-match shortcut uses matching order and the selected snapshot without saving", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const calls: unknown[][] = [];
    const { CompareRolesView } = loadComponent("src/features/pathway/components/CompareRolesView.tsx", {
      ...fixtures(locale),
      "../api": { fetchCompare: async () => failure },
      "@/features/matching/api": { fetchMatches: async (...args: unknown[]) => {
        calls.push(args); return { ok: true, data: { matches: [{ role_id: "synthetic/best" }] } };
      } },
    });
    const html = renderToStaticMarkup(await resolveTree(await CompareRolesView({ scenario: "fast", snapshotDate: "2026-10-13" })));
    assert.ok(html.includes(translations(locale).useTranslations("pathway")("compare.useBestMatch")));
    assert.match(html, /role=synthetic%2Fbest&amp;scenario=fast&amp;snapshot_date=2026-10-13/);
    assert.deepEqual(calls, [["fast", "2026-10-13"]]);
  }
});

test("route and global recovery render translated safe text, retry and a home link", async () => {
  for (const locale of i18n.locales) {
    const intl = translations(locale);
    const t = intl.useTranslations("ui.error");
    let retried = 0;
    const props = { title: t("title"), description: t("unexpected"), home: t("home"), retryLabel: t("retry"), retry: () => retried++ };
    const tree = RouteErrorState(props);
    const html = renderToStaticMarkup(tree);
    const { RouteErrorState: Standalone } = loadComponent("src/features/core/components/RouteErrorState.tsx");
    assert.match(renderToStaticMarkup(React.createElement(Standalone, props)), /href="\/"/, "The real Next Link must render without router providers");
    assert.ok(html.includes(t("unexpected")));
    assert.match(html, /href="\/"/);
    const visit = (node) => {
      if (Array.isArray(node)) return node.forEach(visit);
      if (!React.isValidElement(node)) return;
      if (node.type === "button") node.props.onClick();
      visit(node.props.children);
    };
    visit(tree); assert.equal(retried, 1);
    const common = { ...fixtures(locale), "@/features/core/components/RouteErrorState": { RouteErrorState } };
    const { default: NotFound } = loadComponent("src/app/not-found.tsx", common);
    const notFound = renderToStaticMarkup(await resolveTree(await NotFound({})));
    assert.ok(notFound.includes(t("notFoundTitle")));
    const { default: ErrorPage } = loadComponent("src/app/error.tsx", common);
    const routeTree = await resolveTree(ErrorPage({ reset: props.retry, error: new Error("Do not disclose") }));
    const route = renderToStaticMarkup(routeTree);
    assert.ok(route.includes(t("unexpected")));
    assert.ok(route.includes(t("retry")));
    assert.match(route, /<button/);
    assert.doesNotMatch(route, /Do not disclose|undefined/);
    visit(routeTree); assert.equal(retried, 2);
    const messages = Object.fromEntries(i18n.locales.map((id) => [`../../messages/${id}/ui.json`, { default: JSON.parse(readFileSync(`src/web/messages/${id}/ui.json`, "utf8")) }]));
    const { default: GlobalError } = loadComponent("src/app/global-error.tsx", {
      ...common, ...messages, "./globals.css": {}, "./adept.css": {}, "@/lib/i18n/config": i18n,
      react: { useSyncExternalStore: (_subscribe, snapshot) => snapshot() },
    }, { document: { cookie: `${i18n.LOCALE_COOKIE}=${locale}` } });
    const globalTree = await resolveTree(GlobalError({ reset: props.retry, error: new Error("Do not disclose") }));
    const global = renderToStaticMarkup(globalTree);
    assert.match(global, new RegExp(`<html lang="${locale}"`));
    assert.ok(global.includes(t("unexpected")));
    assert.ok(global.includes(t("retry")));
    assert.match(global, /<button/);
    assert.doesNotMatch(global, /Do not disclose|undefined/);
    visit(globalTree); assert.equal(retried, 3);
  }
});

test("drafts tolerate blocked/corrupt storage, filter stale catalogue IDs and stay account scoped", () => {
  const key = draft.intakeDraftKey("synthetic-a");
  assert.notEqual(key, draft.intakeDraftKey("synthetic-b"));
  const value = { segment: "working", interests: ["data", "retired"], hours_per_week: 8, budget_myr: 200, hrd_eligible: false, learning_style: "mixed", skills: [{ skill_id: "known", level: 3 }, { skill_id: "retired", level: 4 }], step: 3 };
  let raw = "";
  const storage = { getItem: () => raw, setItem: (_key: string, data: string) => { raw = data; }, removeItem: () => { raw = ""; } };
  draft.writeIntakeDraft(storage, key, value);
  const restored = draft.readIntakeDraft(storage, key, new Set(["known"]), ["data"]);
  assert.deepEqual(restored?.skills, [{ skill_id: "known", level: 3 }]);
  assert.deepEqual(restored?.interests, ["data"]);
  assert.equal(restored?.hours_per_week, 8); assert.equal(restored?.budget_myr, 200);
  draft.clearIntakeDraft(storage, key); assert.equal(raw, "");
  raw = "{broken"; assert.equal(draft.readIntakeDraft(storage, key, new Set(), []), null);
  const blocked = () => { throw new Error("Storage blocked"); };
  assert.equal(draft.readIntakeDraft({ getItem: blocked }, key, new Set(), []), null);
  assert.doesNotThrow(() => draft.writeIntakeDraft({ setItem: blocked }, key, value));
  assert.doesNotThrow(() => draft.clearIntakeDraft({ removeItem: blocked }, key));
});

test("intake restores on reload, retains failed saves and clears before successful navigation", async () => {
  const key = draft.intakeDraftKey("synthetic-account");
  let raw = JSON.stringify({ segment: "switcher", interests: ["data"], hours_per_week: 12, budget_myr: 250, hrd_eligible: true, learning_style: "reading", skills: [{ skill_id: "known", level: 4 }], step: 4 });
  const storage = { getItem: () => raw, setItem: (_key: string, data: string) => { raw = data; }, removeItem: (removed: string) => { assert.equal(removed, key); raw = ""; } };
  const states: unknown[] = [], refs: { current: unknown }[] = [], deps: unknown[][] = [], effects: (() => void)[] = [], pending: Promise<unknown>[] = [];
  let stateIndex = 0, refIndex = 0, effectIndex = 0;
  let saveResult: { error?: string; redirectTo?: string } = { error: "network" };
  let target = "";
  const react = {
    useState: (initial: unknown) => {
      const index = stateIndex++; if (!(index in states)) states[index] = initial;
      return [states[index], (value: unknown) => { states[index] = typeof value === "function" ? value(states[index]) : value; }];
    },
    useRef: (current: unknown) => refs[refIndex++] ?? (refs[refIndex - 1] = { current }),
    useEffect: (fn: () => void, next: unknown[]) => {
      const index = effectIndex++;
      if (!deps[index] || next.some((d, i) => d !== deps[index][i])) { deps[index] = next; effects.push(fn); }
    },
    useMemo: (fn: () => unknown) => fn(), startTransition: (fn: () => void) => fn(),
    useTransition: () => [false, (fn: () => unknown) => pending.push(Promise.resolve(fn()))],
  };
  const { IntakeWizard } = loadComponent("src/features/profile/components/IntakeWizard.tsx", {
    react, "next-intl": translations("en"), "@/lib/api/error-message": { errorMessage: (_t, code) => code },
    "next/navigation": { useSearchParams: () => new URLSearchParams(), useRouter: () => ({ replace: (url: string) => { assert.equal(raw, ""); target = url; } }) },
    "@/components/SourceBadge": {}, "@/features/core/components/CvPreview": { CV_SKILLS_KEY: "preview" },
    "../actions": { saveIntakeAction: async (input) => { assert.equal(input.hours_per_week, 12); assert.equal(input.budget_myr, 250); assert.equal(input.skills[0].level, 4); return saveResult; } },
    "../skill-search": skillSearch, "../intake-draft": draft,
  }, { window: { sessionStorage: storage, localStorage: { removeItem: nothing } } });
  const props = { userId: "synthetic-account", catalogue: [{ id: "known", label: "Synthetic skill" }], interests: ["data"], initial: null };
  const render = () => {
    stateIndex = refIndex = effectIndex = 0;
    const tree = IntakeWizard(props); effects.splice(0).forEach((fn) => fn()); return tree;
  };
  render();
  const tree = render();
  const html = renderToStaticMarkup(tree);
  assert.ok(html.includes("Synthetic skill"));
  assert.doesNotMatch(html, /<section[^>]*aria-live/);
  const finish = tree.props.children.at(-1).props.children[1];
  finish.props.onClick(); await Promise.all(pending.splice(0));
  assert.ok(raw); assert.equal(target, "");
  render(); saveResult = { redirectTo: "/app/radar" };
  finish.props.onClick(); await Promise.all(pending.splice(0));
  assert.equal(raw, ""); assert.equal(target, "/app/radar");
  render(); assert.equal(raw, "", "A pending render must not recreate a submitted draft");
});
