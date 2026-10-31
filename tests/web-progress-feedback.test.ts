import assert from "node:assert/strict";
import test from "node:test";

import type { ActionState } from "../src/web/src/features/pathway/action-state.ts";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

const componentPath = "src/features/pathway/components/ProgressToast.tsx";
const key = "adept:progress-toast";

test("queued and live progress feedback survives remounts, expires and unsubscribes", () => {
  for (const blocked of [false, true]) {
    const storage = new Map([[key, "Queued proof"]]);
    const window = new EventTarget();
    let read: () => string | null;
    let serverRead: () => null;
    let subscribe: (callback: () => void) => () => void;
    let expire: () => void;
    let cleared = 0;
    const cleanups: (() => void)[] = [];
    const browserStorage = {
      getItem(name: string) {
        if (blocked) throw new Error("Storage denied");
        return storage.get(name) ?? null;
      },
      setItem(name: string, value: string) {
        if (blocked) throw new Error("Storage denied");
        storage.set(name, value);
      },
      removeItem(name: string) {
        if (blocked) throw new Error("Storage denied");
        storage.delete(name);
      },
    };
    const component = loadComponent(componentPath, {
      react: {
        ...React,
        useSyncExternalStore(sub: (callback: () => void) => () => void, get: () => string | null, getServer: () => null) {
          subscribe = sub; read = get; serverRead = getServer;
          return get();
        },
        useEffect(effect: () => void | (() => void)) {
          const cleanup = effect();
          if (cleanup) cleanups.push(cleanup);
        },
      },
    }, {
      window, sessionStorage: browserStorage, CustomEvent,
      setTimeout(callback: () => void, delay: number) {
        assert.equal(delay, 3500);
        expire = callback;
        return 1;
      },
      clearTimeout() { cleared++; },
    });
    const initial = component.ProgressToast();
    assert.equal(serverRead!(), null, "SSR/hydration starts without browser storage");
    assert.equal(read!(), blocked ? null : "Queued proof");
    if (!blocked) assert.match(renderToStaticMarkup(initial), /Queued proof/);
    let notifications = 0;
    const unsubscribe = subscribe!(() => notifications++);
    component.triggerProgressToast("Proof submitted");
    assert.equal(notifications, 1);
    assert.equal(read!(), "Proof submitted");
    assert.equal(read!(), "Proof submitted", "snapshot stays stable between updates");
    assert.match(renderToStaticMarkup(component.ProgressToast()), /role="status"/);
    assert.match(renderToStaticMarkup(component.ProgressToast()), /Proof submitted/);
    expire!();
    assert.equal(read!(), null, "dismissal stays dismissed even if storage removal fails");
    assert.equal(notifications, 2);
    assert.equal(component.ProgressToast(), null);
    for (const cleanup of cleanups) cleanup();
    assert.ok(cleared > 0);
    unsubscribe();
    component.triggerProgressToast("Later proof");
    assert.equal(notifications, 2, "unmounted subscribers are removed");
  }
});

test("evidence submission keeps failures editable and renders success directly from action state", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const intl = translations(locale);
    let state: ActionState = {};
    let result: ActionState = { error: "unavailable" };
    let pending = false;
    let submit: (previous: ActionState, form: FormData) => Promise<ActionState>;
    const toasts: string[] = [];
    const component = loadComponent("src/features/pathway/components/MarkDoneFlow.tsx", {
      react: {
        ...React,
        useState: () => [true, () => assert.fail("success must not synchronise derived state")],
        useActionState(action: (previous: ActionState, form: FormData) => Promise<ActionState>) { submit = action; return [state, action, pending]; },
      },
      "next-intl": intl,
      "@/components/ui/button": { Button: ({ children, ...props }: { children?: unknown; [key: string]: unknown }) => React.createElement("button", props, children) },
      "@/lib/api/error-message": { errorMessage: () => "Unavailable" },
      "./ProgressToast": { triggerProgressToast: (message: string) => toasts.push(message) },
    });
    const render = () => component.MarkDoneFlow({ action: async () => result, fields: { course_id: "synthetic-course" } });
    render();
    state = await submit!({}, new FormData());
    assert.equal(toasts.length, 0);
    assert.match(renderToStaticMarkup(render()), /role="alert"/);
    result = { done: 1 };
    state = await submit!(state, new FormData());
    assert.deepEqual(toasts, [intl.useTranslations("pathway")("evidence.sent")]);
    pending = true;
    assert.match(renderToStaticMarkup(render()), /<form/);
    pending = false;
    const successNode = render();
    assert.equal(successNode.props.children.props.children, intl.useTranslations("pathway")("evidence.sent"));
    const success = renderToStaticMarkup(successNode);
    assert.doesNotMatch(success, /<form/);
  }
});
