import { ArrowRight, Lock } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

const SKELETON = [0, 1, 2, 3];

/**
 * Signed-out visitors see this when their outlook could not be returned. There is no result to
 * show here, so the blurred area is neutral shapes only: no text, numbers or score-like arcs.
 */
export function CvOutlookGate() {
  const t = useTranslations("ui.landing");
  return (
    <div className="a-locked cv-outlook-gate">
      <div className="a-locked-content" aria-hidden="true">
        {SKELETON.map((i) => (
          <div className="a-ghost" key={i}>
            <span className="a-ghost-ring" />
            <i style={{ width: `${70 - i * 8}%` }} />
            <i style={{ width: `${48 + i * 6}%` }} />
            <i style={{ width: `${60 - i * 5}%` }} />
          </div>
        ))}
      </div>
      <div className="a-locked-cta">
        <span className="a-upload-icon">
          <Lock size={18} aria-hidden />
        </span>
        <h3>{t("guestUnlockTitle")}</h3>
        <p>{t("guestUnlockBody")}</p>
        <div className="a-hero-actions" style={{ justifyContent: "center" }}>
          <Link className="a-btn" href="/auth/signup?next=/app/onboarding">
            {t("unlock")} <ArrowRight size={16} aria-hidden />
          </Link>
          <Link className="a-btn is-ghost" href="/auth/login">
            {t("guestLogIn")}
          </Link>
        </div>
      </div>
    </div>
  );
}
