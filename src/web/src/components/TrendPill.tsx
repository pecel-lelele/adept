import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import { useTranslations } from "next-intl";

/** A skill's demand direction as a word with an arrow, never a bare symbol. */
export function TrendPill({ direction }: { direction?: string | null }) {
  const t = useTranslations("common.design");
  const tp = useTranslations("ui.page");
  if (!direction) {
    return (
      <span className="a-trend" data-dir="none">
        {tp("notTracked")}
      </span>
    );
  }
  const Icon = direction === "rising" ? TrendingUp : direction === "declining" ? TrendingDown : Minus;
  const key = direction === "rising" || direction === "declining" ? direction : "stable";
  return (
    <span className="a-trend" data-dir={key}>
      <Icon size={14} strokeWidth={2} aria-hidden /> {t(key)}
    </span>
  );
}
