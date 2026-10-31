import Link from "next/link";
import { useTranslations } from "next-intl";

import type { RecommendationMeta } from "@/lib/api";

import type { TrendProvenanceNotice } from "./TrendProvenanceNotice";

/**
 * Attribution without clutter: one small link to the consolidated sources on "Data and AI use".
 * The estimate label and snapshot date sit in the link's tooltip and accessible name, so screen
 * readers and hover still say the figures are dated estimates (AGENTS.md section 3.4).
 */
export function MetaBar({ meta }: { meta: RecommendationMeta & Parameters<typeof TrendProvenanceNotice>[0]["meta"] & { data_provenance_note?: string | null } }) {
  const t = useTranslations("common.design");
  const te = useTranslations("common.estimate");
  const tf = useTranslations("common.freshness");
  const label = [
    meta.is_estimate ? te("hint") : null,
    meta.snapshot_date,
    meta.is_fallback ? tf("fallbackShort") : null,
    meta.is_replay === null ? tf("unverifiedShort") : null,
  ].filter(Boolean).join(" · ");
  return (
    <p className="a-sourcelink">
      <Link href="/about#data-sources" title={label} aria-label={`${t("sources")}. ${label}`}>{t("sources")}</Link>
    </p>
  );
}
