import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { call, errorBody } from "../src/web/src/lib/api/client.ts";
import * as errors from "../src/web/src/lib/api/error-message.ts";
import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

const nothing = () => {};
const link = { default: ({ children, replace: _replace, scroll: _scroll, prefetch: _prefetch, ...props }) => React.createElement("a", props, children) };

test("API failures return codes even with missing or malformed bodies and never forward backend prose", async () => {
  assert.deepEqual(errorBody({ error: { code: "pdf_encrypted" } }, 422), { code: "pdf_encrypted" });
  assert.deepEqual(errorBody({ error: { code: "email_taken", message: "Backend English with private details" } }, 409), { code: "email_taken" });
  for (const body of [null, {}, { error: null }, { error: "bad" }, { error: { code: 42 } }, { error: { code: "not a code" } }]) {
    assert.deepEqual(errorBody(body, 401), { code: "unauthorized" });
    assert.deepEqual(errorBody(body, 503), { code: "server_error" });
  }
  assert.deepEqual(errorBody(null, 429), { code: "rate_limited" });
  const network = await call(Promise.reject(new TypeError("synthetic connection failure")));
  assert.deepEqual(network, { ok: false, status: 0, code: "network" });
});

test("every error code has EN/MS/ZH copy and unfamiliar codes render a translated fallback", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const ui = JSON.parse(readFileSync(new URL(`../src/web/messages/${locale}/ui.json`, import.meta.url), "utf8"));
    assert.deepEqual(Object.keys(ui.apiErrors).sort(), [...errors.API_ERROR_CODES].sort());
    const intl = translations(locale);
    const t = intl.useTranslations("ui.apiErrors");
    for (const code of errors.API_ERROR_CODES) {
      const message = errors.errorMessage(t, code);
      assert.ok(message && message !== "undefined" && message !== code, `${locale}: ${code}`);
    }
    assert.equal(errors.errorMessage(t, "future_unrecognized_code"), t("error"));
    const { ErrorState } = loadComponent("src/components/ErrorState.tsx", {
      "@/lib/api/error-message": errors,
      "next-intl/server": { getTranslations: async (ns) => intl.useTranslations(ns) },
      "next/link": link,
      "./RetryButton": { RetryButton: ({ label }) => React.createElement("button", {}, label) },
    });
    const html = renderToStaticMarkup(await resolveTree(await ErrorState({ failure: {
      ok: false, code: "future_unrecognized_code", status: 500, message: "Backend English with private details",
    } })));
    assert.ok(html.includes(t("error")));
    assert.doesNotMatch(html, /Backend English|future_unrecognized_code/);
  }
});

function authActions(failure = { ok: false, status: 401, code: "invalid_credentials" }) {
  return loadComponent("src/features/core/auth-actions.ts", {
    "next/cache": { revalidatePath: nothing }, "next/navigation": { redirect: nothing },
    "@/lib/api": { call: async () => failure, getApi: async () => ({ POST: nothing }) },
    "@/lib/auth/session": {}, "@/lib/navigation": {},
  });
}

test("auth and join actions return error codes, preserve form values and never retain a password", async () => {
  const { loginAction, signupAction, joinOrgAction, deleteAccountAction } = authActions();
  const form = new FormData();
  form.set("email", "synthetic@example.test");
  form.set("password", "synthetic password");
  const login = await loginAction({}, form);
  assert.equal(login.error, "invalid_credentials");
  assert.equal(login.values.email, "synthetic@example.test");
  assert.equal(login.values.password, undefined);
  assert.equal((await deleteAccountAction({}, form)).error, "confirmation_required");
  form.set("confirm", "on");
  const wrongPassword = authActions({ ok: false, status: 401, code: "incorrect_password" });
  assert.equal((await wrongPassword.deleteAccountAction({}, form)).error, "incorrect_password");
  const expired = authActions({ ok: false, status: 401, code: "unauthorized" });
  assert.equal((await expired.deleteAccountAction({}, form)).error, "unauthorized");
  form.set("join_code", "SYNTHETIC");
  // Sharing skill levels is optional, so signup reaches the API without it.
  assert.equal((await signupAction({}, form)).error, "invalid_credentials");
  assert.equal((await joinOrgAction({}, form)).error, "consent_required");
  form.set("consent", "on");
  assert.equal((await joinOrgAction({}, form)).error, "invalid_credentials");
  form.set("share_skills", "on");
  const denied = authActions({ ok: false, status: 422, code: "bad_join_code" });
  assert.equal((await denied.joinOrgAction({}, form)).error, "bad_join_code");
  assert.equal((await denied.signupAction({}, form)).error, "bad_join_code");
});

function profileActions(callResult = async () => ({ ok: false, status: 503, code: "storage_unavailable" })) {
  return loadComponent("src/features/profile/actions.ts", {
    "next/cache": { revalidatePath: nothing }, "next/navigation": { redirect: nothing },
    "@/lib/api": { API_URL: "https://synthetic.example.test", call: callResult, getApi: async () => ({ POST: nothing, PUT: nothing }) },
    "@/lib/api/client": { errorBody }, "@/lib/auth/session": { getSessionToken: async () => undefined },
  });
}

test("intake actions report local and API validation codes without English messages", async () => {
  const { saveIntakeAction } = profileActions();
  assert.equal((await saveIntakeAction({ skills: [] })).error, "skill_required");
  const input = { segment: "working", interests: [], hours_per_week: 4, budget_myr: 0, hrd_eligible: false, learning_style: "mixed", skills: [{ skill_id: "python", level: 2 }] };
  assert.equal((await saveIntakeAction(input)).error, "storage_unavailable");
  let count = 0;
  const actions = profileActions(async () => ++count === 1 ? { ok: true, data: {} } : { ok: false, code: "unknown_skill", status: 422 });
  assert.equal((await actions.saveIntakeAction(input)).error, "unknown_skill");
});

test("CV actions return codes for file validation, parser rejection and connection failure", async (t) => {
  let offline = false;
  t.mock.method(globalThis, "fetch", async () => {
    if (offline) throw new TypeError("synthetic offline test");
    return Response.json({ error: { code: "pdf_encrypted", message: "Backend English" } }, { status: 422 });
  });
  const { uploadCvAction } = profileActions();
  const form = new FormData();
  assert.equal((await uploadCvAction(form)).error, "choose_file");
  form.set("file", new File([new Uint8Array(5 * 1024 * 1024 + 1)], "synthetic.txt"));
  assert.equal((await uploadCvAction(form)).error, "payload_too_large");
  form.set("file", new File(["Synthetic CV"], "synthetic.txt", { type: "text/plain" }));
  assert.equal((await uploadCvAction(form)).error, "pdf_encrypted");
  offline = true;
  assert.equal((await uploadCvAction(form)).error, "cv_read_failed");
});

test("auth, join and deletion forms display translated codes in the current locale", () => {
  for (const locale of ["en", "ms", "zh"]) {
    for (const [name, code] of [["AuthView", "invalid_credentials"], ["JoinView", "sharing_consent_required"], ["AccountDataCard", "confirmation_required"]]) {
      const intl = translations(locale);
      const { [name]: Component } = loadComponent(`src/features/core/components/${name}.tsx`, {
        "@/lib/api/error-message": errors, "next-intl": intl, "next/link": link,
        "next/navigation": { usePathname: () => "/auth/login", useSearchParams: () => new URLSearchParams() },
        react: { useActionState: () => [{ error: code }, nothing, false], useState: (value) => [name === "AccountDataCard" ? true : value, nothing] },
        "../auth-actions": { loginAction: nothing, signupAction: nothing, joinOrgAction: nothing, deleteAccountAction: nothing },
        "@/components/shell/Brand": { BrandMark: nothing },
        "@/components/viz/FeatureArt": { FeatureArt: nothing }, "@/components/viz/OrgScene": { OrgScene: nothing }, "@/components/viz/PathScene": { PathScene: nothing },
      });
      const html = renderToStaticMarkup(React.createElement(Component));
      assert.ok(html.includes(intl.useTranslations("ui.apiErrors")(code)), `${locale}: ${name}`);
      assert.doesNotMatch(html, new RegExp(`>${code}<`));
    }
  }
});
