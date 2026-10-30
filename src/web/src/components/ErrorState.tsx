import { CircleAlert, UserRoundPen, WifiOff } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import type { ApiFailure } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/error-message";

import { RetryButton } from "./RetryButton";

/** A failed API call with the one action that fixes it: sign in, finish the profile, retry. */
export async function ErrorState({ failure, compact = false }: { failure: ApiFailure; compact?: boolean }) {
  const t = await getTranslations("ui.error");
  const te = await getTranslations("ui.apiErrors");
  const needsProfile = failure.code === "profile_required";
  const needsLogin = failure.status === 401;
  const Icon = needsProfile ? UserRoundPen : failure.code === "network" ? WifiOff : CircleAlert;
  const body = (
    <div className="a-empty">
      <span className="a-empty-icon">
        <Icon size={24} aria-hidden />
      </span>
      <strong style={{ color: "var(--a-ink)" }}>{needsProfile ? t("profile") : t("title")}</strong>
      <span>{errorMessage(te, failure.code)}</span>
      {needsProfile ? (
        <Link className="a-btn is-small" href="/app/onboarding">
          {t("profile")}
        </Link>
      ) : needsLogin ? (
        <form method="post" action="/auth/logout">
          <button type="submit" className="a-btn is-small">{t("signIn")}</button>
        </form>
      ) : (
        <RetryButton label={t("retry")} />
      )}
    </div>
  );
  return compact ? body : <section className="a-card">{body}</section>;
}
