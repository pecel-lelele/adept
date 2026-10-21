import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { Card, CardContent, CardHeader, CardTitle } from "@/components";
import type { ScenarioId, Schemas } from "@/lib/api";
import { journeyHref } from "@/lib/navigation";

type Segment = NonNullable<Schemas["Pathway"]["segment"]>;

function nextLink(segment: Segment, scenario: ScenarioId): string {
  if (segment === "working") return "/app/courses?hrd_claimable=true";
  if (segment === "graduate") return "/app/courses?max_cost_myr=0";
  return `/app/matches?scenario=${scenario}`; // keep the scenario the learner is viewing
}

/** What to do next, worded for the learner's segment. The plan above is the same for everyone. */
export async function SegmentGuide({
  segment,
  scenario,
  roleId,
}: {
  segment: Segment | null | undefined;
  scenario: ScenarioId;
  roleId?: string;
}) {
  if (!segment) return null;
  const t = await getTranslations("pathway");
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t(`guide.${segment}.title`)}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>{t(`guide.${segment}.body`)}</p>
        <Link
          href={journeyHref(
            nextLink(segment, scenario),
            new URLSearchParams({
              scenario,
              ...(roleId ? { role: roleId } : {}),
            }),
          )}
          className="underline"
        >
          {t(`guide.${segment}.link`)}
        </Link>
        <p className="text-xs text-muted-foreground">{t("guide.sameplan")}</p>
      </CardContent>
    </Card>
  );
}
