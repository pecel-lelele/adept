import assert from "node:assert/strict";
import test from "node:test";

import * as scenario from "../src/web/src/lib/scenario.ts";
import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

function findAll(node, predicate) {
  if (Array.isArray(node)) return node.flatMap((child) => findAll(child, predicate));
  if (!React.isValidElement(node)) return [];
  return [...(predicate(node) ? [node] : []), ...findAll(node.props.children, predicate)];
}

function toggle(path: string, query: string, locale = "en") {
  const { ScenarioToggle } = loadComponent("src/components/ScenarioToggle.tsx", {
    "next-intl": translations(locale), "@/lib/scenario": scenario,
    "next/navigation": {
      usePathname: () => path, useSearchParams: () => new URLSearchParams(query),
      useRouter: () => { throw new Error("Scenario changes must not wait on an RSC transition"); },
    },
  });
  return ScenarioToggle({});
}

test("scenario navigation uses a native GET with every filter preserved and one selected scenario", () => {
  for (const path of ["/app/radar", "/app/matches", "/app/pathway", "/org/radar", "/org/plan"]) {
    for (const current of scenario.SCENARIOS) {
      const tree = toggle(path, `scenario=${current}&role=data-analyst&snapshot_date=2026-10-13&sdg=0.25&tag=a&tag=b&scenario=invalid`);
      const [form] = findAll(tree, (node) => node.type === "form");
      assert.equal(form.props.method, "get");
      assert.equal(form.props.action, path);
      assert.equal(form.props.onSubmit, undefined, "the browser must own the navigation");
      const inputs = findAll(form, (node) => node.type === "input");
      const buttons = findAll(form, (node) => node.type === "button");
      for (const button of buttons) {
        assert.equal(button.props.type, "submit");
        assert.equal(button.props.disabled, undefined);
        assert.equal(button.props["aria-disabled"], undefined);
        const query = new URLSearchParams(inputs.map((input) => [input.props.name, input.props.value]));
        query.append(button.props.name, button.props.value);
        assert.deepEqual(query.getAll("scenario"), [button.props.value]);
        assert.deepEqual(query.getAll("tag"), ["a", "b"]);
        assert.equal(query.get("role"), "data-analyst");
        assert.equal(query.get("snapshot_date"), "2026-10-13");
        assert.equal(query.get("sdg"), "0.25");
        let prevented = false;
        button.props.onClick({ preventDefault: () => { prevented = true; } });
        assert.equal(prevented, button.props.value === current);
      }
    }
  }
});

test("scenario arrows submit the focused option without trapping keyboard users", () => {
  for (const current of scenario.SCENARIOS) {
    const tree = toggle("/app/matches", `scenario=${current}`);
    const buttons = findAll(tree, (node) => node.type === "button");
    const currentButton = buttons.find((button) => button.props.value === current);
    assert.equal(currentButton.props.tabIndex, 0);
    const other = buttons.find((button) => button !== currentButton);
    assert.equal(other.props.tabIndex, -1);
    let focused = false;
    let submitted;
    let prevented = false;
    const form = {
      querySelector: () => ({ form, value: other.props.value }),
      requestSubmit: (button) => { submitted = button.value; },
    };
    currentButton.props.onKeyDown({
      key: "ArrowRight", preventDefault: () => { prevented = true; },
      currentTarget: {
        form,
        closest: () => ({ querySelectorAll: () => buttons.map(() => ({ focus: () => { focused = true; } })) }),
      },
    });
    assert.ok(prevented && focused);
    assert.equal(submitted, other.props.value);
  }
});

test("the server-rendered scenario form is usable before hydration in every locale", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const html = renderToStaticMarkup(toggle("/app/radar", "scenario=fast", locale));
    assert.match(html, /<form[^>]*action="\/app\/radar"[^>]*method="get"/);
    for (const value of scenario.SCENARIOS) {
      const button = html.match(new RegExp(`<button[^>]*value="${value}"[^>]*>`))?.[0] ?? "";
      assert.match(button, /type="submit"/);
      assert.match(button, /name="scenario"/);
    }
    assert.doesNotMatch(html, /aria-busy|aria-disabled|disabled=""/);
    assert.ok(html.includes(translations(locale).useTranslations("common.scenario")("hint")));
  }
});
