import assert from "node:assert/strict";
import test from "node:test";

import * as draft from "../src/web/src/features/profile/intake-draft.ts";
import * as navigation from "../src/web/src/config/navigation.ts";
import * as skillSearch from "../src/web/src/features/profile/skill-search.ts";
import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

function find(node: unknown, predicate: (element: React.ReactElement) => boolean): React.ReactElement | undefined {
  if (Array.isArray(node)) return node.map((child) => find(child, predicate)).find(Boolean);
  if (!React.isValidElement(node)) return undefined;
  if (predicate(node)) return node;
  return find(node.props.children, predicate);
}

function wizard(initialStep: number) {
  const states: unknown[] = [];
  const refs: { current: unknown }[] = [];
  const effects: (() => void)[] = [];
  const pending: Promise<unknown>[] = [];
  let stateIndex = 0, refIndex = 0, uploads = 0;
  const react = {
    useState: (initial: unknown) => {
      const index = stateIndex++;
      if (!(index in states)) states[index] = index === 0 ? initialStep : initial;
      return [states[index], (value: unknown) => { states[index] = typeof value === "function" ? value(states[index]) : value; }];
    },
    useRef: (current: unknown) => refs[refIndex++] ?? (refs[refIndex - 1] = { current }),
    useEffect: (fn: () => void, deps: unknown[]) => { if (deps.length === 1 && typeof deps[0] === "number") effects.push(fn); },
    useMemo: (fn: () => unknown) => fn(),
    startTransition: (fn: () => void) => fn(),
    useTransition: () => [false, (fn: () => unknown) => pending.push(Promise.resolve(fn()))],
  };
  const { IntakeWizard } = loadComponent("src/features/profile/components/IntakeWizard.tsx", {
    react, "next-intl": translations("en"), "next/navigation": { useRouter: () => ({ replace() {} }), useSearchParams: () => new URLSearchParams() },
    "@/lib/api/error-message": { errorMessage: (_t: unknown, code: string) => code },
    "@/components/SourceBadge": {}, "@/features/core/components/CvPreview": { CV_SKILLS_KEY: "preview" },
    "../skill-search": skillSearch, "../intake-draft": draft,
    "../actions": { uploadCvAction: async () => { uploads++; return { skills: [] }; } },
  });
  const render = () => { stateIndex = refIndex = 0; return IntakeWizard({ userId: "synthetic-test", catalogue: [], interests: [], initial: null }); };
  return { render, effects, pending, get uploads() { return uploads; } };
}

test("CV chooser and drop reject invalid files before sending, and allow a supported file", async () => {
  const view = wizard(4);
  let tree = view.render();
  const chooser = find(tree, (el) => el.type === "input" && el.props.type === "file");
  const drop = find(tree, (el) => typeof el.props.onDrop === "function");
  assert.ok(chooser && drop);
  const choose = (file: File) => chooser.props.onChange({ target: { files: [file], value: "selected" } });
  choose(new File([new Uint8Array(5 * 1024 * 1024 + 1)], "oversize.pdf", { type: "application/pdf" }));
  assert.equal(view.uploads, 0);
  tree = view.render();
  assert.ok(renderToStaticMarkup(tree).includes(translations("en").useTranslations("ui.intake")("uploadTypeError")));
  choose(new File(["x"], "script.sh", { type: "application/x-sh" }));
  assert.equal(view.uploads, 0);
  drop.props.onDrop({ preventDefault() {}, stopPropagation() {}, dataTransfer: { files: [new File(["x"], "script.sh")] } });
  assert.equal(view.uploads, 0);
  choose(new File(["Skills: spreadsheet analysis"], "synthetic.txt", { type: "text/plain" }));
  await Promise.all(view.pending);
  assert.equal(view.uploads, 1);
});

test("wizard moves focus to the new step heading on Next and Back", () => {
  const view = wizard(1);
  let tree = view.render();
  find(tree, (el) => el.type === "button" && el.props.children === "Continue")?.props.onClick();
  tree = view.render();
  const heading = find(tree, (el) => el.type === "h2");
  assert.ok(heading);
  assert.equal(heading.props.tabIndex, -1);
  let focused = 0;
  heading.props.ref.current = { focus: () => focused++ };
  view.effects.splice(0).forEach((effect) => effect());
  assert.equal(focused, 1);
  find(tree, (el) => el.type === "button" && el.props.children === "Back")?.props.onClick();
  tree = view.render();
  const backHeading = find(tree, (el) => el.type === "h2");
  assert.ok(backHeading);
  backHeading.props.ref.current = { focus: () => focused++ };
  view.effects.splice(0).forEach((effect) => effect());
  assert.equal(focused, 2);
});

test("completed sidebar stages and skill suggestions have accessible names", () => {
  const intl = translations("en");
  const { SideNav } = loadComponent("src/components/shell/Nav.tsx", {
    "next-intl": { useTranslations: (namespace: string) => namespace === "ui.page"
      ? (key: string) => key === "state.done" ? "done" : intl.useTranslations(namespace)(key)
      : intl.useTranslations(namespace) },
    "next/navigation": { usePathname: () => "/app", useSearchParams: () => new URLSearchParams() },
    "next/link": { default: ({ children, ...props }: React.PropsWithChildren) => React.createElement("a", props, children) },
    "@/config/navigation": navigation, "@/lib/navigation": { journeyHref: (href: string) => href },
  });
  const html = renderToStaticMarkup(React.createElement(SideNav, { ws: navigation.learnerWorkspace, doneSteps: [1] }));
  assert.match(html, /My skills[\s\S]*?class="a-sr">done<\/span>/);
  const view = wizard(4);
  const tree = view.render();
  const search = find(tree, (el) => el.type === "input" && el.props.placeholder === "Search the skill bank");
  assert.ok(search);
  search.props.onChange({ target: { value: "spreadsheet" } });
  const result = renderToStaticMarkup(view.render());
  assert.match(result, /role="listbox" aria-label="Search the skill bank"/);
});
