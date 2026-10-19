/** Result of a pathway server action; `error` is shown next to the button that failed. */
export type ActionState = { error?: string };

/** Turn an openapi-fetch error result into a short message (API body first, then status). */
export function actionError(error: unknown, status: number): string {
  if (error && typeof error === "object" && "error" in error) {
    const body = (error as { error?: { message?: string } }).error;
    if (body?.message) return body.message;
  }
  if (status === 429) return "Too many requests. Please wait a minute and try again.";
  return `Request failed (${status}).`;
}
