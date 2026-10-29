import assert from "node:assert/strict";
import test from "node:test";

import { journeyHref } from "../src/web/src/lib/navigation.ts";
import * as navigation from "../src/web/src/config/navigation.ts";
import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

function find(node, predicate) {
  if (Array.isArray(node)) return node.map((child) => find(child, predicate)).find(Boolean);
  if (!React.isValidElement(node)) return undefined;
  if (predicate(node)) return node;
  return find(node.props.children, predicate);
}

test("radar Latest clears snapshot_date and normal journey links never inherit historical mode", () => {
  let current = new URL("https://example.test/app/radar?scenario=fast");
  const { SignalExplorer } = loadComponent("src/features/trends/components/SignalExplorer.tsx", {
    "next-intl": translations(),
    "next/navigation": {
      useRouter: () => ({ push: (href) => { current = new URL(href, current); } }),
      usePathname: () => current.pathname,
      useSearchParams: () => current.searchParams,
    },
    react: { useState: (value) => [value, () => {}], useTransition: () => [false, (fn) => fn()] },
    "@/components/useBusy": { useBusy: () => {} },
  });
  const select = () => find(SignalExplorer({ items: [], scenario: "fast", dates: ["2026-10-13"] }), (node) => node.type === "select");
  assert.equal(select().props.value, "");
  select().props.onChange({ target: { value: "2026-10-13" } });
  assert.equal(current.searchParams.get("snapshot_date"), "2026-10-13");
  assert.equal(journeyHref("/app/pathway?role=data-analyst", current.searchParams), "/app/pathway?role=data-analyst&scenario=fast");
  select().props.onChange({ target: { value: "" } });
  assert.equal(current.searchParams.has("snapshot_date"), false);
  assert.equal(select().props.value, "");
  assert.equal(journeyHref("/app/matches", current.searchParams), "/app/matches?scenario=fast");
});

test("historical pathway Back to latest restores the visible Save plan action", async () => {
  const link = { default: ({ href, children, ...props }) => React.createElement("a", { href, ...props }, children) };
  const intl = translations();
  const saveLabel = intl.useTranslations("pathway")("plan.save");
  const { HistoricalSnapshotBanner } = loadComponent("src/components/HistoricalSnapshotBanner.tsx", {
    "next-intl": intl, "next/link": link,
  });
  const passthrough = ({ children }) => React.createElement("div", {}, children);
  const nothing = () => null;
  const plan = {
    role_id: "data-analyst", role_label: "Synthetic role", steps: [], total_weeks: 0,
    within_budget: true, warnings: [], unmet: [], meta: {},
  };
  const { PathwayView } = loadComponent("src/features/pathway/components/PathwayView.tsx", {
    "@/config/navigation": navigation,
    "next-intl/server": { getTranslations: async (ns) => intl.useTranslations(ns) },
    "next/link": link,
    "@/components": { ErrorState: nothing, MetaBar: nothing, Kpis: nothing,
      PageHeader: ({ actions, children }) => React.createElement("header", {}, actions, children) },
    "@/components/Fold": { Fold: passthrough },
    "@/components/HistoricalSnapshotBanner": { HistoricalSnapshotBanner },
    "@/features/jobs": { CareerRoadmap: nothing, CertificationsCard: nothing, RoleOpeningsCard: nothing },
    "../actions": { acceptReplanAction: nothing, savePlanAction: nothing },
    "../api": { fetchPathway: async () => ({ ok: true, data: plan }), fetchPlanStatus: async () => ({ ok: true, data: { saved: null } }) },
    "./ActionForm": { ActionForm: ({ label }) => React.createElement("button", {}, label) },
    "./PathwaySteps": { PathwaySteps: nothing },
  });
  const historical = await PathwayView({ roleId: "data-analyst", scenario: "fast", snapshotDate: "2026-10-13" });
  const html = renderToStaticMarkup(await resolveTree(historical));
  assert.match(html, /Viewing snapshot 2026-10-13/);
  assert.ok(!html.includes(`<button>${saveLabel}</button>`));
  const href = html.match(/href="([^"]+)">Back to latest/)[1].replaceAll("&amp;", "&");
  const destination = new URL(href, "https://example.test");
  assert.equal(destination.searchParams.has("snapshot_date"), false);
  assert.equal(destination.searchParams.get("role"), "data-analyst");
  const latest = await PathwayView({ roleId: destination.searchParams.get("role"), scenario: destination.searchParams.get("scenario") });
  const latestHtml = renderToStaticMarkup(await resolveTree(latest));
  assert.ok(latestHtml.includes(`<button>${saveLabel}</button>`));
  assert.doesNotMatch(latestHtml, /Viewing snapshot/);
});
