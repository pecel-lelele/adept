import { AsyncLocalStorage } from "node:async_hooks";
import type { Request, Response as ExpressResponse } from "express";

export const requestContext = new AsyncLocalStorage<{ req: Request; res: ExpressResponse }>();
function context() {
  const value = requestContext.getStore();
  if (!value) throw new Error("Request context required");
  return value;
}
export async function cookies() {
  const { req, res } = context();
  return {
    get(name: string) {
      const value = req.cookies?.[name];
      return value ? { name, value } : undefined;
    },
    set(name: string, value: string, options: any = {}) {
      res.cookie(name, value, { ...options, maxAge: options.maxAge ? options.maxAge * 1000 : undefined });
      req.cookies[name] = value;
    },
    delete(name: string) {
      res.clearCookie(name, { path: "/" });
      delete req.cookies[name];
    },
  };
}
export async function headers() {
  const { req } = context();
  const result = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (value) result.set(key, Array.isArray(value) ? value.join(", ") : value);
  }
  const referer = req.get("referer");
  result.set("x-adept-path", referer ? new URL(referer).pathname : "/app");
  return result;
}
export class Redirect extends Error {
  constructor(public location: string) { super("Redirect"); }
}
export function redirect(location: string): never { throw new Redirect(location); }
export function revalidatePath() { /* Client refreshes after an action. */ }

export class NextResponse extends Response {
  cookies = {
    set: (name: string, value: string, options?: any) => { void cookies().then(c => c.set(name, value, options)); },
    delete: (name: string) => { void cookies().then(c => c.delete(name)); },
  };
  static redirect(url: string | URL, status = 307) {
    return new NextResponse(null, { status, headers: { location: String(url) } });
  }
}
