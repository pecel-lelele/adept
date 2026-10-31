import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

for (const locale of ["en", "ms", "zh"]) {
  test(`scenario comparison attribution names both scenarios (${locale})`, () => {
    const intl = translations(locale);
    const { EstimateLabel } = loadComponent("src/components/EstimateLabel.tsx", { "next-intl": intl });
    const t = intl.useTranslations("common");
    const render = (props: Record<string, unknown>) => renderToStaticMarkup(React.createElement(EstimateLabel, props));
    const both = render({ scenario: "both" });
    assert.ok(both.includes(t("estimate.label")));
    assert.ok(both.includes(t("scenario.moderate")));
    assert.ok(both.includes(t("scenario.fast")));
    for (const scenario of ["moderate", "fast"]) {
      const single = render({ scenario });
      assert.ok(single.includes(t(`scenario.${scenario}`)));
      assert.ok(!single.includes("undefined"));
    }
    assert.equal(render({ scenario: "both", isEstimate: false }), "");
  });
}
