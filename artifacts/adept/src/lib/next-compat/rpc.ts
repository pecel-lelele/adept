import { navigate, refresh, withBase } from "./router";

/**
 * Calls an original server action through the backend RPC bridge (POST /api/rpc).
 * FormData arguments travel as form entries prefixed "form:<index>:".
 */
export async function rpc<T>(module: string, name: string, args: unknown[], revalidate = true): Promise<T> {
  const body = new FormData();
  body.set("module", module);
  body.set("export", name);
  const encoded = args.map((arg, i) => {
    if (arg instanceof FormData) {
      for (const [key, value] of arg.entries()) body.append(`form:${i}:${key}`, value);
      return { $form: true };
    }
    return arg === undefined ? null : arg;
  });
  body.set("args", JSON.stringify(encoded));
  const response = await fetch(withBase("/api/rpc"), { method: "POST", body, credentials: "include" });
  const json = (await response.json().catch(() => null)) as { result?: T; redirect?: string; error?: string } | null;
  if (json?.redirect) {
    refresh();
    navigate(json.redirect);
    return {} as T;
  }
  if (!response.ok || !json || json.error) {
    throw new Error(json?.error ?? `Request failed (${response.status}).`);
  }
  if (revalidate) refresh();
  return json.result as T;
}
