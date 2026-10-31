import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import test from "node:test";
import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

const run = {
  run_id: "00000000-0000-0000-0000-000000000056", status: "running",
  started_at: "2026-10-30T03:41:00Z", data_as_of: "2026-10-25", shared: false,
  steps: [
    { source: "trends", status: "running" }, { source: "jobs", status: "pending" },
    { source: "courses", status: "done" }, { source: "labour", status: "failed" },
  ],
};

function render(phase: string, extra: Record<string, unknown> = {}, locale = "en") {
  const { RefreshProgressView } = loadComponent("src/features/trends/components/RefreshDataButton.tsx", {
    "next-intl": translations(locale), "next/navigation": {}, "../refresh-actions": {},
  });
  return renderToStaticMarkup(React.createElement(RefreshProgressView, {
    state: { phase, elapsed: 17, dataAsOf: "2026-10-25", checkedAt: Date.now(), ...extra }, onRefresh() {},
  }));
}

for (const locale of ["en", "ms", "zh"]) {
  test(`${locale}: refresh states render production components with accessible, translated feedback`, () => {
    const t = translations(locale).useTranslations("trends.refreshUser");
    const idle = render("idle", {}, locale);
    assert.ok(idle.includes(t("title")));
    assert.doesNotMatch(idle, /disabled/);
    const checking = render("checking", {}, locale);
    assert.match(checking, /disabled=""/);
    assert.ok(checking.includes(t("checking")));
    const latest = render("up_to_date", {}, locale);
    assert.ok(latest.includes(t("latest", { date: "2026-10-25" })));
    assert.doesNotMatch(latest, /a-refresh-panel|aria-busy/);
    const running = render("running", { run }, locale);
    assert.match(running, /aria-live="polite"/);
    assert.match(running, /aria-busy="true"/);
    for (const step of run.steps) {
      assert.ok(running.includes(t(`sources.${step.source}`)));
      assert.ok(running.includes(t(`states.${step.status}`)));
    }
    assert.ok(running.includes(t("warmup")));
    assert.doesNotMatch(render("running", { run, elapsed: 0 }, locale), /a-refresh-panel/);
    assert.ok(render("done", {}, locale).includes(t("done", { date: "2026-10-25" })));
    const failed = render("failed", {}, locale);
    assert.ok(failed.includes(t("failed", { date: "2026-10-25" })));
    assert.ok(failed.includes(t("retry")));
    assert.doesNotMatch(failed, /disabled/);
    assert.ok(render("cooldown", { retryAt: new Date(Date.now() + 420000).toISOString() }, locale).includes(t("cooldown", { minutes: "7" })));
    assert.ok(render("running", { run: { ...run, shared: true } }, locale).includes(t("shared")));
    // Partial success (trends done, jobs failed) shows each source's terminal result.
    const partial = {
      ...run,
      status: "failed",
      steps: [{ source: "trends", status: "done", rows: 3 }, { source: "jobs", status: "failed", rows: 0 }],
    };
    const terminal = render("failed", { run: partial }, locale);
    assert.match(terminal, /data-refresh-result="per-source"/);
    assert.match(terminal, /data-status="done"/);
    assert.match(terminal, /data-status="failed"/);
    assert.ok(terminal.includes(t("sources.trends")) && terminal.includes(t("sources.jobs")));
    assert.doesNotMatch(render("done", {}, locale), /per-source/);
  });
}

test("refresh messages have identical keys in every locale, and motion can be disabled", () => {
  const keys = (item: Record<string, unknown>, prefix = ""): string[] => Object.entries(item).flatMap(([key, value]) =>
    typeof value === "object" && value !== null ? keys(value as Record<string, unknown>, `${prefix}${key}.`) : [`${prefix}${key}`]).sort();
  const read = (locale: string) => JSON.parse(readFileSync(`src/web/messages/${locale}/trends.json`, "utf8")).refreshUser;
  assert.deepEqual(keys(read("ms")), keys(read("en")));
  assert.deepEqual(keys(read("zh")), keys(read("en")));
  const css = readFileSync("src/web/src/app/adept.css", "utf8");
  assert.match(css, /prefers-reduced-motion: reduce[^}]*\}[\s\S]*?a-refresh-spinner/);
});

test("the date line uses the selected snapshot's observations, not a newer global snapshot", async () => {
  const intl = translations("en");
  const { DataAsOf } = loadComponent("src/components/DataAsOf.tsx", {
    "next-intl/server": { getTranslations: async (namespace) => intl.useTranslations(namespace) },
    "@/lib/data-sources": { fetchDataSources: async () => ({ ok: true, data: { sources: [{
      source: "trends", data_as_of: "2026-10-25", snapshot_date: "2026-10-25", source_name: "arXiv",
      is_fallback: false, is_stale: false,
    }] } }) },
  });
  const html = renderToStaticMarkup(await DataAsOf({ source: "trends", meta: {
    snapshot_date: "2026-10-13", observed_to: "2024-10-12", sources: [{ name: "Historical arXiv" }], is_fallback: true,
  } }));
  assert.match(html, /Data as of 2024-10-12/);
  assert.match(html, /Historical observations replayed as snapshot 2026-10-13/);
  assert.doesNotMatch(html, /Data as of 2026-10-25/);
});

test("selected snapshot date and source remain visible when global freshness is unavailable", async () => {
  const intl = translations("en");
  const { DataAsOf } = loadComponent("src/components/DataAsOf.tsx", {
    "next-intl/server": { getTranslations: async (namespace) => intl.useTranslations(namespace) },
    "@/lib/data-sources": { fetchDataSources: async () => ({ ok: false, code: "storage_unavailable" }) },
  });
  const html = renderToStaticMarkup(await DataAsOf({ source: "trends", meta: {
    snapshot_date: "2026-10-20", observed_to: "2026-10-19", is_fallback: true,
    sources: [{ name: "Synthetic trend source", url: "https://example.test", retrieved_at: "2026-10-20" }],
  } }));
  assert.match(html, /Data as of 2026-10-19/);
  assert.match(html, /Synthetic trend source/);
  assert.doesNotMatch(html, /undefined/);
  assert.equal(await DataAsOf({ source: "trends" }), null);
});

test("a partially failed run refreshes successful cards and retains its failed state", async () => {
  const phases: string[] = [];
  let refreshed = 0;
  const hooks = {
    ...React,
    useState: (initial: unknown) => {
      let value = initial;
      return [value, (update: unknown) => {
        value = typeof update === "function" ? update(value) : update;
        if (value && typeof value === "object" && "phase" in value) phases.push(String(value.phase));
      }];
    },
    useRef: (value: unknown) => ({ current: value }),
    useCallback: (callback: unknown) => callback,
    useEffect() {},
    useTransition: () => [false, (callback: () => void) => callback()],
  };
  const { RefreshDataButton } = loadComponent("src/features/trends/components/RefreshDataButton.tsx", {
    react: hooks, "next/navigation": { useRouter: () => ({ refresh() { refreshed += 1; } }) },
    "../refresh-actions": { checkRefresh: async () => ({ ok: true, data: { ...run, status: "failed" } }) },
  });
  const element = RefreshDataButton({ dataAsOf: "2026-10-25" });
  await element.props.onRefresh();
  assert.deepEqual(phases, ["checking", "failed"]);
  assert.equal(refreshed, 1);
});

// Optional local screenshots use these exact production renders, never hand-drawn mockups.
if (process.env.REFRESH_SCREENSHOT_HTML) {
  mkdirSync("src/data/raw/refresh-screenshots", { recursive: true });
  const css = readFileSync("src/web/src/app/adept.css", "utf8");
  for (const phase of ["running", "failed"]) writeFileSync(`src/data/raw/refresh-screenshots/${phase}.html`,
    `<!doctype html><html lang="en"><meta charset="utf-8"><title>Adept · Refresh data</title><style>${css}</style><body class="a-page"><main style="max-width:800px;margin:48px auto;padding:24px"><h1>Adept · AI trend radar</h1>${render(phase, { run })}</main></body></html>`);
}
