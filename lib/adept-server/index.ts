export { requestContext, Redirect } from "./context";
import * as auth from "./source/features/core/auth-actions";
import * as profile from "./source/features/profile/actions";
import * as pathway from "./source/features/pathway/actions";
import * as org from "./source/features/org/actions";
import * as funding from "./source/features/org/funding-actions";
import * as programmes from "./source/features/org/programmes/actions";
import * as work from "./source/features/org/work/actions";
import * as preview from "./source/app/api/preview/route";
import * as assistant from "./source/app/api/assistant/route";
import * as workspace from "./source/app/api/workspace/route";
import * as accountExport from "./source/app/api/account/export/route";
import * as logout from "./source/app/auth/logout/route";

export const actions: Record<string, Record<string, Function>> = {
  "features/core/auth-actions.ts": auth,
  "features/profile/actions.ts": profile,
  "features/pathway/actions.ts": pathway,
  "features/org/actions.ts": org,
  "features/org/funding-actions.ts": funding,
  "features/org/programmes/actions.ts": programmes,
  "features/org/work/actions.ts": work,
};
export const handlers: Record<string, any> = {
  "/api/preview": preview,
  "/api/assistant": assistant,
  "/api/workspace": workspace,
  "/api/account/export": accountExport,
  "/api/logout": logout,
};
