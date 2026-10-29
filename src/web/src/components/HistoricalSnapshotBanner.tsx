import Link from "next/link";
import { useTranslations } from "next-intl";

export function HistoricalSnapshotBanner({ date, latestHref }: { date?: string; latestHref: string }) {
  const t = useTranslations("common.freshness");
  if (!date) return null;
  return (
    <p className="a-notice" data-tone="info" role="status">
      {t("historical", { date })} <Link href={latestHref}>{t("backToLatest")}</Link>
    </p>
  );
}
