import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";

const web = fileURLToPath(new URL("../../src/web/", import.meta.url));
const webRequire = createRequire(resolve(web, "package.json"));
const ts = webRequire("typescript");

/** Render production TSX with the existing compiler; replace only framework request hooks. */
export function loadComponent(path: string, overrides: Record<string, unknown> = {}) {
  const filename = resolve(web, path);
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  runInNewContext(code, {
    module, exports: module.exports,
    require: (id: string) => {
      if (id in overrides) return overrides[id];
      if (id.startsWith("./")) {
        return loadComponent(resolve(dirname(filename), `${id}.tsx`), overrides);
      }
      return webRequire(id);
    },
  }, { filename });
  return module.exports as Record<string, (props: Record<string, unknown>) => unknown>;
}

export const React = webRequire("react");
export const { renderToStaticMarkup } = webRequire("react-dom/server");

export function translations(locale = "en") {
  const common = JSON.parse(readFileSync(resolve(web, `messages/${locale}/common.json`), "utf8"));
  return {
    useTranslations: (namespace: string) => (key: string, values: Record<string, string> = {}) => {
      let value = { common };
      for (const part of `${namespace}.${key}`.split(".")) value = value[part];
      return String(value).replace(/\{(\w+)\}/g, (_, name: string) => values[name] ?? name);
    },
  };
}
