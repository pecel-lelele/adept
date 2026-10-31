import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import test from "node:test";

import * as navigation from "../src/web/src/config/navigation.ts";
import * as scenario from "../src/web/src/lib/scenario.ts";
import * as skillSearch from "../src/web/src/features/profile/skill-search.ts";
import * as intakeDraft from "../src/web/src/features/profile/intake-draft.ts";
import * as cvHandoff from "../src/web/src/features/profile/cv-handoff.ts";
import * as errorMessages from "../src/web/src/lib/api/error-message.ts";
import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

const nothing = () => null;
const link = { default: ({ href, children, ...props }) => React.createElement("a", { href, ...props }, children) };

test("zero matches render actionable empty states in every locale", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const intl = translations(locale);
    const server = { getTranslations: async (ns) => intl.useTranslations(ns) };
    const { EmptyState } = loadComponent("src/components/EmptyState.tsx");
    const { PageHeader } = loadComponent("src/components/PageHeader.tsx");
    const { ErrorState } = loadComponent("src/components/ErrorState.tsx", {
      "@/lib/api/error-message": errorMessages,
      "next-intl/server": server, "next/link": link,
      "./RetryButton": { RetryButton: ({ label }) => React.createElement("button", {}, label) },
    });
    const common = {
      "next-intl/server": server, "next-intl": intl, "next/link": link,
      "@/config/navigation": navigation,
      "@/components": { EmptyState, ErrorState, PageHeader, MetaBar: nothing, EstimateLabel: nothing, Badge: nothing, SdgBadge: nothing },
      "@/components/ErrorState": { ErrorState },
      "@/components/DataAsOf": { DataAsOf: () => null },
      "@/components/HistoricalSnapshotBanner": { HistoricalSnapshotBanner: nothing },
      "@/components/viz": { scoreColour: () => "inherit" },
      "@/features/jobs": { fetchJobsSummary: async () => ({ ok: true, data: { roles: [] } }) },
      "@/features/trends/api": { fetchRadar: async () => ({ ok: false }) },
      "@/features/matching/api": { fetchMatches: async () => ({ ok: false }) },
      "@/components/Fold": { Fold: nothing },
      "./SnapshotPicker": { SnapshotPicker: nothing }, "./SdgWeightSlider": { SdgWeightSlider: nothing },
      "./ReplayChanges": { ReplayChanges: nothing }, "./MatchImprovements": { MatchImprovements: nothing },
      "./MatchSdgTargets": { MatchSdgTargets: nothing },
      "./ProfileNote": { ProfileNote: nothing }, "./ActionForm": { ActionForm: nothing },
      "../actions": { savePlanAction: nothing },
      "@/features/pathway/actions": { savePlanAction: nothing },
      "@/features/pathway/api": { fetchPlanStatus: async () => ({ ok: false }) },
      "@/features/pathway/components/ActionForm": { ActionForm: nothing },
    };
    let result = { ok: true, data: { matches: [], meta: {} } };
    const { MatchesView } = loadComponent("src/features/matching/components/MatchesView.tsx", {
      ...common, "../api": { fetchMatches: async () => result, fetchReplay: nothing },
    });
    const matches = renderToStaticMarkup(await resolveTree(await MatchesView({ scenario: "fast" })));
    assert.ok(matches.includes(intl.useTranslations("matching")("emptyTitle")));
    assert.match(matches, /href="\/app\/profile"/);
    
    result = { ok: false, status: 0, code: "network", message: "synthetic failure" };
    const failed = renderToStaticMarkup(await resolveTree(await MatchesView({ scenario: "fast" })));
    assert.ok(failed.includes(intl.useTranslations("ui.error")("retry")));
    assert.ok(failed.includes(intl.useTranslations("ui.apiErrors")("network")));
    assert.ok(!failed.includes(intl.useTranslations("matching")("emptyTitle")));
  }
});

test("intake Finish shows a disabled Saving state while the save transition is pending", () => {
  for (const locale of ["en", "ms", "zh"]) {
    let states = 0;
    let transitions = 0;
    const { IntakeWizard } = loadComponent("src/features/profile/components/IntakeWizard.tsx", {
      "next/navigation": { useSearchParams: () => new URLSearchParams(), useRouter: () => ({ replace: nothing }) },
      "@/lib/api/error-message": errorMessages,
      "next-intl": translations(locale),
      react: { useState: (value) => [states++ === 0 ? 4 : value, nothing], useMemo: (fn) => fn(), useRef: (current) => ({ current }), useTransition: () => [++transitions === 3, nothing], useEffect: nothing, startTransition: nothing },
      "@/components/SourceBadge": { SourceBadge: nothing },
      "@/features/core/components/CvPreview": { CV_SKILLS_KEY: "synthetic-preview" },
      "../actions": { resolveSkillAction: nothing, saveIntakeAction: nothing, uploadCvAction: nothing },
      "../skill-search": skillSearch,
      "../intake-draft": intakeDraft,
      "../cv-handoff": cvHandoff,
    });
    const html = renderToStaticMarkup(React.createElement(IntakeWizard, { catalogue: [], interests: [], initial: null }));
    assert.match(html, /disabled="" aria-busy="true"/);
    assert.ok(html.includes(translations(locale).useTranslations("ui.intake")("saving")));
  }
});

test("six learner stages and four organisation stages drive translated totals; the scenario hint is visible", () => {
  assert.deepEqual(navigation.allItems(navigation.learnerWorkspace).filter((item) => item.step).map((item) => item.step), [1, 2, 3, 4, 5, 6]);
  assert.equal(navigation.journeyStepCount(), 6);
  assert.equal(navigation.journeyStepCount(navigation.orgWorkspace), 4);
  for (const locale of ["en", "ms", "zh"]) {
    const { ScenarioToggle } = loadComponent("src/components/ScenarioToggle.tsx", {
      "next-intl": translations(locale), "@/lib/scenario": scenario,
      "@/components/useBusy": { useBusy: nothing },
      "next/navigation": { useRouter: () => ({ push: nothing }), usePathname: () => "/app/matches", useSearchParams: () => new URLSearchParams() },
      react: { useTransition: () => [false, nothing] },
    });
    const html = renderToStaticMarkup(React.createElement(ScenarioToggle));
    assert.match(html, /<small[^>]*>[^<]+<\/small>/);
    assert.ok(html.includes(translations(locale).useTranslations("common.scenario")("hint")));
  }
});

test("retry refreshes the route and every API failure call site uses ErrorState", () => {
  let refreshed = 0;
  const { RetryButton } = loadComponent("src/components/RetryButton.tsx", {
    "next/navigation": { useRouter: () => ({ refresh: () => refreshed++ }) },
    react: { useTransition: () => [false, (fn) => fn()] },
  });
  RetryButton({ label: "Synthetic retry" }).props.onClick();
  assert.equal(refreshed, 1);
  for (const folder of ["app", "features"]) {
    const root = new URL(`../src/web/src/${folder}/`, import.meta.url);
    for (const name of readdirSync(root, { recursive: true })) {
      if (name.endsWith(".tsx")) assert.doesNotMatch(readFileSync(new URL(name.replaceAll("\\", "/"), root), "utf8"), /\bApiError\b/, name);
    }
  }
});
