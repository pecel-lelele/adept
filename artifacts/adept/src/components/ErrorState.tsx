import { asyncView } from "@/lib/next-compat/async-view";
import { CircleAlert, UserRoundPen, WifiOff } from "lucide-react";
import Link from "@/lib/next-compat/link";
import { getTranslations } from "@/lib/next-compat/intl";

import type { ApiFailure } from "@/lib/api/client";

import { RetryButton } from "./RetryButton";

/** A failed API call with the one action that fixes it: sign in, finish the profile, retry. */
async function ErrorStateAsync({ failure, compact = false }: { failure: ApiFailure; compact?: boolean }) {
  const t = await getTranslations("ui.error");
  const needsProfile = failure.code === "profile_required";
  const needsLogin = failure.status === 401;
  const Icon = needsProfile ? UserRoundPen : failure.code === "network" ? WifiOff : CircleAlert;
  const body = (
    <div className="a-empty">
      <span className="a-empty-icon">
        <Icon size={24} aria-hidden />
      </span>
      <strong style={{ color: "var(--a-ink)" }}>{needsProfile ? t("profile") : t("title")}</strong>
      <span>{failure.code === "network" ? t("network") : failure.message}</span>
      {needsProfile ? (
        <Link className="a-btn is-small" href="/app/onboarding">
          {t("profile")}
        </Link>
      ) : needsLogin ? (
        <a className="a-btn is-small" href="/api/logout">
          {t("signIn")}
        </a>
      ) : (
        <RetryButton label={t("retry")} />
      )}
    </div>
  );
  return compact ? body : <section className="a-card">{body}</section>;
}

export const ErrorState = asyncView(ErrorStateAsync);
