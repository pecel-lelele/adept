import { CircleAlert, UserRoundPen, WifiOff } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import type { ApiFailure } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/error-message";

import { RetryButton } from "./RetryButton";
import { SignInAgainButton } from "./SignInAgainButton";

/** A failed API call with the one action that fixes it: sign in, finish the profile, retry. */
export async function ErrorState({ failure, compact = false }: { failure: ApiFailure; compact?: boolean }) {
  const t = await getTranslations("ui.error");
  const te = await getTranslations("ui.apiErrors");
  const needsProfile = failure.code === "profile_required";
  const needsCohort = failure.code === "insufficient_cohort";
  const needsLogin = failure.status === 401;
  const Icon = needsProfile ? UserRoundPen : failure.code === "network" ? WifiOff : CircleAlert;
  const body = (
    <div className="a-empty" role="status" aria-live="polite">
      <span className="a-empty-icon">
        <Icon size={24} aria-hidden />
      </span>
      <strong style={{ color: "var(--a-ink)" }}>{needsProfile ? t("profile") : needsCohort ? t("cohort") : t("title")}</strong>
      <span>{errorMessage(te, failure.code)}</span>
      {needsProfile ? (
        <Link className="a-btn is-small" href="/app/onboarding">
          {t("profile")}
        </Link>
      ) : needsCohort ? (
        <Link className="a-btn is-small" href="/org/members">
          {t("members")}
        </Link>
      ) : needsLogin ? (
        <SignInAgainButton label={t("signIn")} />
      ) : (
        <RetryButton label={t("retry")} />
      )}
    </div>
  );
  return compact ? body : <section className="a-card">{body}</section>;
}
