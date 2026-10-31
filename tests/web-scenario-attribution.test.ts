import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

for (const locale of ["en", "ms", "zh"]) {
  test(`estimate attribution stays screen-reader-only in every scenario (${locale})`, () => {
    const intl = translations(locale);
    const { EstimateLabel } = loadComponent("src/components/EstimateLabel.tsx", { "next-intl": intl });
    const t = intl.useTranslations("common");
    const render = (props: Record<string, unknown>) => renderToStaticMarkup(React.createElement(EstimateLabel, props));
    for (const scenario of ["moderate", "fast", "both"]) {
      const html = render({ scenario });
      assert.ok(html.includes(t("estimate.label")));
      assert.ok(html.includes(t("estimate.hint")));
      assert.doesNotMatch(html, /undefined|Moderate AI change|Fast AI change/);
    }
    assert.equal(render({ scenario: "both", isEstimate: false }), "");
  });
}
