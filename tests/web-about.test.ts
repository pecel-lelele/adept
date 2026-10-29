import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

const registry = JSON.parse(readFileSync(new URL("../src/api/app/features/guardrails/registry.json", import.meta.url), "utf8"));

test("About renders every model and data register entry, with translated purposes even when Adi is disabled", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    for (const enabled of [false, true]) {
      const intl = translations(locale);
      const nothing = () => null;
      const payloads = {
        disclosure: { llm_enabled: enabled, provider: enabled ? "runpod" : "none", model: enabled ? "glm-5.3" : "",
          purpose: [], rules: [], registry, calls_logged: 0, rejected_ids: 0 },
        sources: { sources: [] },
        fairness: { passed: true, counterfactual_checks: [], protected_attributes: [] },
      };
      const { AboutView } = loadComponent("src/features/guardrails/components/AboutView.tsx", {
        "next-intl/server": { getTranslations: async (ns) => intl.useTranslations(ns) },
        "@/components": { ApiError: nothing, Badge: ({ children }) => React.createElement("span", {}, children) },
        "@/components/shell/Site": { SiteHeader: nothing, SiteFooter: nothing },
        "@/lib/api": { call: async (data) => ({ ok: true, data }), getApi: async () => ({ GET: (path) => payloads[path.split("/").at(-1)] }) },
      });
      const html = renderToStaticMarkup(await resolveTree(await AboutView({})));
      for (const entry of registry) {
        assert.ok(html.includes(entry.name), `${locale}: missing ${entry.id}`);
        assert.ok(html.includes(`href="${entry.url}"`));
        const purpose = intl.useTranslations("guardrails")(`registryPurpose.${entry.id}`);
        assert.notEqual(purpose, "undefined");
        assert.ok(html.includes(purpose), `${locale}: missing purpose ${entry.id}`);
      }
      assert.ok(html.includes(intl.useTranslations("guardrails")("llmSummary")));
      assert.doesNotMatch(html, /No language model is used/);
    }
  }
});
