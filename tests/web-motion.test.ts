import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";

const require = createRequire(new URL("../src/web/package.json", import.meta.url));
const ts = require("typescript");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

test("page entrance preserves streamed score text while descendant hydration is pending", () => {
  const effects: Array<() => void> = [];
  const frames: Array<(time: number) => void> = [];
  const score = { textContent: "41", dataset: {} };
  const main = { querySelectorAll: () => [score] };
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(new URL("../src/web/src/components/shell/Motion.tsx", import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  runInNewContext(code, {
    module, exports: module.exports,
    document: { getElementById: () => main },
    window: { matchMedia: () => ({ matches: false }) },
    performance: { now: () => 0 },
    requestAnimationFrame: (callback: (time: number) => void) => frames.push(callback),
    require: (id: string) => {
      if (id === "next/navigation") return { usePathname: () => "/app/matches" };
      if (id === "react") return { ...React, useEffect: (effect: () => void) => effects.push(effect) };
      return require(id);
    },
  });
  const child = React.createElement("strong", {}, score.textContent);
  const element = module.exports.PageEnter({ children: child });
  const before = renderToStaticMarkup(element);
  for (const effect of effects) effect();
  // A parent effect can run before its streamed descendants hydrate. React still expects
  // the server's exact text at that point, including when a scenario transition starts.
  for (const frame of frames.splice(0)) frame(0);
  assert.equal(score.textContent, "41");
  assert.equal(element.props.children, child);
  assert.equal(renderToStaticMarkup(element), before);
});
