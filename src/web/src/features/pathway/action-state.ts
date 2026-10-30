import { errorBody } from "@/lib/api/client";

/** Result of a pathway server action; `error` is a translated-on-display code. */
export type ActionState = { error?: string; done?: number };

/** Use the same error-code parser as all other API callers. */
export function actionError(error: unknown, status: number): string {
  return errorBody(error, status).code;
}
