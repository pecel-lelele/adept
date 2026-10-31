import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

const link = { default: ({ href, children, ...props }: Record<string, unknown>) => React.createElement("a", { href, ...props }, children) };

for (const locale of ["en", "ms", "zh"]) {
  test(`guest outlook gate offers sign-up and log-in with no result data (${locale})`, () => {
    const intl = translations(locale);
    const t = intl.useTranslations("ui.landing");
    const { CvOutlookGate } = loadComponent("src/features/core/components/CvOutlookGate.tsx", { "next-intl": intl, "next/link": link });
    const html = renderToStaticMarkup(React.createElement(CvOutlookGate));
    assert.ok(html.includes(t("guestUnlockTitle")));
    assert.ok(html.includes(t("guestUnlockBody")));
    assert.ok(html.includes('href="/auth/signup?next=/app/onboarding"'));
    assert.ok(html.includes('href="/auth/login"'));
    assert.ok(html.includes(t("guestLogIn")));

    const blurred = html.match(/<div class="a-locked-content" aria-hidden="true">(.*)<\/div><div class="a-locked-cta">/)?.[1];
    assert.ok(blurred, "the blurred area is hidden from screen readers");
    // Only empty shapes: drop tags and any styling, and nothing readable may remain.
    assert.equal(blurred.replace(/<[^>]*>/g, ""), "");
    assert.doesNotMatch(html, /\d+\s*%<|\d\/5|role_id|score/i);
  });
}
