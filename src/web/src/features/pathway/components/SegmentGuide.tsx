import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { Card, CardContent, CardHeader, CardTitle } from "@/components";
import type { Schemas } from "@/lib/api";

type Segment = NonNullable<Schemas["Pathway"]["segment"]>;

const NEXT_LINK: Record<Segment, string> = {
  working: "/app/courses?hrd_claimable=true",
  graduate: "/app/courses?max_cost_myr=0",
  switcher: "/app/matches",
};

/** What to do next, worded for the learner's segment. The plan above is the same for everyone. */
export async function SegmentGuide({ segment }: { segment: Segment | null | undefined }) {
  if (!segment) return null;
  const t = await getTranslations("pathway");
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t(`guide.${segment}.title`)}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>{t(`guide.${segment}.body`)}</p>
        <Link href={NEXT_LINK[segment]} className="underline">
          {t(`guide.${segment}.link`)}
        </Link>
        <p className="text-xs text-muted-foreground">{t("guide.sameplan")}</p>
      </CardContent>
    </Card>
  );
}
