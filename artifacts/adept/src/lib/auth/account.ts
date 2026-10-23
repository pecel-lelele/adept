import { call, getApi, type Schemas } from "@/lib/api";
import { getGeneration } from "@/lib/next-compat/router";

import { getSessionToken } from "./session";

export type Account = Schemas["Account"];

let cached: { generation: number; promise: Promise<Account | null> } | undefined;

/** The signed-in account, or null. Cached until the next router refresh. */
export function getAccount(): Promise<Account | null> {
  const generation = getGeneration();
  if (!cached || cached.generation !== generation) {
    const promise = (async () => {
      if (!(await getSessionToken())) return null;
      const api = await getApi();
      const result = await call(api.GET("/api/v1/auth/me"));
      return result.ok ? result.data : null;
    })();
    cached = { generation, promise };
  }
  return cached.promise;
}
