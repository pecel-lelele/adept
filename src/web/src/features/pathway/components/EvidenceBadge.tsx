import { getTranslations } from "next-intl/server";

import { Badge } from "@/components";
import type { Schemas } from "@/lib/api";

type Evidence = Schemas["CompletionEvidence"];

/** Shows how strongly a completion is evidenced, weakest to strongest. */
export async function EvidenceBadge({ evidence }: { evidence: Evidence | null }) {
  const t = await getTranslations("pathway");
  if (!evidence) return <Badge variant="outline">{t("evidence.kind.self_reported")}</Badge>;
  const variant =
    evidence.kind === "org_confirmed"
      ? "success"
      : evidence.kind === "org_rejected"
        ? "danger"
        : "outline";
  return (
    <span className="flex flex-wrap items-center gap-1 text-xs">
      <Badge variant={variant}>{t(`evidence.kind.${evidence.kind}`)}</Badge>
      {evidence.kind === "certificate_link" ? (
        <span className="text-muted-foreground">
          {t(`evidence.link.${evidence.link_status === "provider_verified" ? "submitted" : evidence.link_status ?? "not_submitted"}`)}
        </span>
      ) : null}
    </span>
  );
}
