import assert from "node:assert/strict";
import test from "node:test";

import { teamCtaFor } from "../src/web/src/features/core/team-cta.ts";
import { translations } from "./harness/web-components.ts";

const origin = "https://adept.example.test";

test("signed out: set up a team goes to team signup; 'I manage a team already' signs in to /org", () => {
  const cta = teamCtaFor(null);
  assert.deepEqual(cta.primary, { href: "/auth/signup?mode=organisation", label: "tCta", signOutFirst: false });
  assert.ok(cta.secondary);
  const login = new URL(cta.secondary.href, origin);
  assert.equal(login.pathname, "/auth/login");
  assert.equal(login.searchParams.get("next"), "/org");
  assert.equal(cta.secondary.label, "tSignIn");
});

test("a team manager gets one primary button that opens the team workspace", () => {
  const cta = teamCtaFor({ kind: "org_admin" });
  assert.deepEqual(cta.primary, { href: "/org", label: "tCtaOpen", signOutFirst: false });
  assert.equal(cta.secondary, null);
});

for (const [state, account] of [
  ["a personal learner", { kind: "learner" }],
  ["an organisation member", { kind: "learner", org_id: "synthetic-org" }],
] as const) {
  test(`${state}: create a team account signs out first; joining with a code goes to /app/join`, () => {
    const cta = teamCtaFor(account);
    assert.equal(cta.primary.label, "tCtaCreate");
    assert.equal(cta.primary.signOutFirst, true);
    const logout = new URL(cta.primary.href, origin);
    assert.equal(logout.pathname, "/auth/logout");
    assert.equal(logout.searchParams.get("next"), "/auth/signup?mode=organisation&role=team");
    assert.deepEqual(cta.secondary, { href: "/app/join", label: "tCtaJoin", signOutFirst: false });
  });
}

test("/app/join is never labelled as setting up or managing a team, in any locale", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const t = translations(locale).useTranslations("ui.landing");
    for (const account of [null, { kind: "org_admin" }, { kind: "learner" }]) {
      const cta = teamCtaFor(account);
      for (const link of [cta.primary, cta.secondary]) {
        if (!link) continue;
        const label = t(link.label);
        assert.ok(label.length > 0 && label !== link.label, `${locale}: ${link.label}`);
        if (link.href === "/app/join") assert.notEqual(link.label, "tCta");
        if (link.href === "/app/join") assert.notEqual(link.label, "tSignIn");
      }
    }
  }
});
