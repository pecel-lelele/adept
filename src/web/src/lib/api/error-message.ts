import type { Messages } from "next-intl";

type ErrorKey = keyof Messages["ui"]["apiErrors"];

export const API_ERROR_CODES = [
  "error", "network", "unauthorized", "invalid_credentials", "incorrect_password",
  "server_error", "forbidden", "not_found", "method_not_allowed", "conflict",
  "profile_required", "insufficient_cohort", "storage_unavailable", "rate_limited", "validation_error", "bad_request",
  "skill_required", "choose_file", "payload_too_large", "cv_read_failed", "wrong_file_type",
  "pdf_unsupported", "pdf_no_text", "pdf_unreadable", "pdf_encrypted", "docx_unreadable", "docx_no_text",
  "unknown_reference", "unknown_skill", "consent", "consent_required", "sharing_consent_required",
  "bad_join_code", "email_taken", "organisation_required", "confirmation_required", "last_manager",
  "trend_unavailable",
  "ceiling_exceeded", "mandatory", "reason_required", "role_required", "unknown_member",
  "stale_package", "stale_programme", "evidence_changed", "workspace_changed",
  "funding_conflict", "disallowed_content", "unknown_course", "invalid_role_proposal",
] as const satisfies readonly ErrorKey[];

const codes: ReadonlySet<string> = new Set(API_ERROR_CODES);

/** API/action codes never render as raw prose; unfamiliar codes receive a translated fallback. */
export function errorMessage(t: (key: ErrorKey) => string, code: string): string {
  return t(codes.has(code) ? code as ErrorKey : "error");
}
