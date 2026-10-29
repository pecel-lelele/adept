import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

test("join has separate, initially unticked membership and skill-sharing checkboxes", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const { JoinView } = loadComponent("src/features/core/components/JoinView.tsx", {
      "next-intl": translations(locale),
      react: { useActionState: () => [{}, undefined, false] },
      "next/link": { default: ({ children, ...props }) => React.createElement("a", props, children) },
      "../auth-actions": { joinOrgAction: () => {} },
    });
    const html = renderToStaticMarkup(React.createElement(JoinView));
    for (const name of ["consent", "share_skills"]) {
      const input = html.match(new RegExp(`<input[^>]*name="${name}"[^>]*>`))?.[0] ?? "";
      assert.match(input, /type="checkbox"/);
      assert.match(input, /required=""/);
    }
    assert.doesNotMatch(html, /checked=""/);
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
    "@/lib/auth/session": {}, "@/lib/navigation": {},
  });
  const form = new FormData();
  form.set("code", "SYNTHETIC");
  form.set("consent", "on");
  const missing = await joinOrgAction({}, form);
  assert.ok(missing.error);
  assert.equal(calls, 0);
  form.set("share_skills", "on");
  await joinOrgAction({}, form);
  assert.equal(calls, 1);
  assert.equal(submitted.share_skills, true);
});
