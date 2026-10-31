import assert from "node:assert/strict";
import test from "node:test";
import * as errorMessages from "../src/web/src/lib/api/error-message.ts";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

test("join has separate, initially unticked membership and skill-sharing checkboxes", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const { JoinView } = loadComponent("src/features/core/components/JoinView.tsx", {
      "@/lib/api/error-message": errorMessages,
      "next-intl": translations(locale),
      react: { useActionState: () => [{}, undefined, false] },
      "next/link": { default: ({ children, ...props }) => React.createElement("a", props, children) },
      "../auth-actions": { joinOrgAction: () => {} },
    });
    const html = renderToStaticMarkup(React.createElement(JoinView));
    for (const name of ["consent", "share_skills"]) {
      const input = html.match(new RegExp(`<input[^>]*name="${name}"[^>]*>`))?.[0] ?? "";
      assert.match(input, /type="checkbox"/);
      // Joining needs consent; sharing skill levels is optional and never pre-ticked.
      if (name === "consent") assert.match(input, /required=""/);
      else assert.doesNotMatch(input, /required=""/);
    }
    assert.doesNotMatch(html, /checked=""/);
    assert.match(html, /href="\/privacy"/);
    const signOut = translations(locale).useTranslations("ui.join")("teamAccountSignOut");
    assert.ok(html.includes(signOut.replaceAll("'", "&#x27;")), "creating a team account says it signs you out");
    const signup = html.match(/<form[^>]*action="([^"]*\/auth\/logout[^"]*)"[^>]*>/);
    assert.ok(signup, "team signup submits the POST-only logout handler");
    assert.match(signup[0], /method="post"/);
    const url = new URL(signup[1], "https://adept.example.test");
    assert.equal(url.pathname, "/auth/logout");
    assert.equal(url.searchParams.get("next"), "/auth/signup?mode=organisation&role=team");
    assert.doesNotMatch(html, /href="\/auth\/logout/);
  }
});

test("joining never infers skill sharing from membership consent", async () => {
  let calls = 0;
  let submitted;
  const intl = translations();
  const { joinOrgAction } = loadComponent("src/features/core/auth-actions.ts", {
    "next/cache": { revalidatePath: () => {} },
    "next/navigation": { redirect: () => {} },
    "next-intl/server": { getTranslations: async (namespace) => intl.useTranslations(namespace) },
    "@/lib/api": {
      getApi: async () => ({ POST: (_path, { body }) => { calls++; submitted = body; return { name: "Synthetic org", id: "synthetic-org" }; } }),
      call: async (data) => ({ ok: true, data }),
    },
    "@/lib/auth/session": {}, "@/lib/auth/workspace": {}, "@/lib/navigation": {},
  });
  const form = new FormData();
  form.set("code", "SYNTHETIC");
  form.set("consent", "on");
  // Not ticking the sharing box joins without sharing: false is sent, never inferred as true.
  const unshared = await joinOrgAction({}, form);
  assert.equal(unshared.error, undefined);
  assert.equal(calls, 1);
  assert.equal(submitted.share_skills, false);
  form.set("share_skills", "on");
  await joinOrgAction({}, form);
  assert.equal(calls, 2);
  assert.equal(submitted.share_skills, true);
  form.delete("consent");
  assert.equal((await joinOrgAction({}, form)).error, "consent_required");
  assert.equal(calls, 2);
});
