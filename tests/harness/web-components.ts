import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";

const web = fileURLToPath(new URL("../../src/web/", import.meta.url));
const webRequire = createRequire(resolve(web, "package.json"));
const ts = webRequire("typescript");

/** Render production TSX with the existing compiler; replace only framework request hooks. */
export function loadComponent(path: string, overrides: Record<string, unknown> = {}, globals: Record<string, unknown> = {}) {
  const filename = resolve(web, path);
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  runInNewContext(code, {
    ...globals,
    module, exports: module.exports, URLSearchParams, URL, File, FormData, AbortSignal, fetch,
    require: (id: string) => {
      if (id in overrides) return overrides[id];
      // Attribution link needs next/link + intl context; component tests render without it.
      if (id === "@/components/MetaBar") return { MetaBar: () => null };
      if (id.startsWith("./")) {
        return loadComponent(resolve(dirname(filename), `${id}.tsx`), overrides, globals);
      }
      return webRequire(id);
    },
  }, { filename });
  return module.exports as Record<string, (props: Record<string, unknown>) => unknown>;
}

export const React = webRequire("react");
export const { renderToStaticMarkup } = webRequire("react-dom/server");

export function translations(locale = "en") {
  return {
    useTranslations: (namespace: string) => (key: string, values: Record<string, string> = {}) => {
      const [file, ...parts] = `${namespace}.${key}`.split(".");
      let value = JSON.parse(readFileSync(resolve(web, `messages/${locale}/${file}.json`), "utf8"));
      for (const part of parts) value = value[part];
      return String(value).replace(/\{(\w+)\}/g, (_, name: string) => values[name] ?? name);
    },
  };
}

/** Resolve async server children before rendering their actual HTML with React DOM. */
export async function resolveTree(node: unknown): Promise<unknown> {
  if (Array.isArray(node)) return Promise.all(node.map(resolveTree));
  if (!React.isValidElement(node)) return node;
  if (typeof node.type === "function") return resolveTree(await node.type(node.props));
  const children = await resolveTree(node.props.children);
  return Array.isArray(children) ? React.cloneElement(node, {}, ...children) : React.cloneElement(node, {}, children);
}
