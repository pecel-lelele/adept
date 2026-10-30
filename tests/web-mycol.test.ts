import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

test("MyCOL badge renders historical source metadata and translated limits in every locale", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const intl = translations(locale);
    const { MetaBar } = loadComponent("src/components/MetaBar.tsx", { "next-intl": intl });
    const { CriticalOccupationBadge } = loadComponent("src/features/matching/components/CriticalOccupationBadge.tsx", {
      "next-intl/server": { getTranslations: async (namespace) => intl.useTranslations(namespace) },
      "@/components": { MetaBar },
    });
    const url = "https://www.talentcorp.com.my/report.pdf#page=137";
    const badge = {
      edition: "2024/2025", masco4d: "2524", occupation_label: "Data Professionals",
      matched_title: "Data Analyst", source_page: 272, pdf_page: 137,
      meta: { sources: [{ name: "TalentCorp MyCOL 2024/2025", url, retrieved_at: "2026-10-29" }],
        snapshot_date: "2026-10-29", scenario: "moderate", is_estimate: false },
    };
    const html = renderToStaticMarkup(await resolveTree(await CriticalOccupationBadge({ badge })));
    assert.match(html, /MASCO 2524/);
    assert.match(html, /Data Analyst/);
    assert.match(html, /2024\/2025/);
    assert.match(html, /2026-10-29/);
    assert.ok(html.includes(`href="${url}"`));
    assert.ok(html.includes(intl.useTranslations("matching")("criticalOccupationNote")));
    assert.equal(renderToStaticMarkup(await CriticalOccupationBadge({ badge: null })), "");
  }
});
