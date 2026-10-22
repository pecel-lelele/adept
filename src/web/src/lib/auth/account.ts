import { cache } from "react";

import { call, getApi, type Schemas } from "@/lib/api";

import { getSessionToken } from "./session";

export type Account = Schemas["Account"];

/** The signed-in account, or null. Cached for one server render. */
export const getAccount = cache(async (): Promise<Account | null> => {
  if (!(await getSessionToken())) return null;
  const api = await getApi();
  const result = await call(api.GET("/api/v1/auth/me"));
  return result.ok ? result.data : null;
});
