import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ApiError, Badge, Card, CardHeader, CardTitle, PageHeader, StubBanner } from "@/components";

import { fetchMyProfile } from "../api";

const SEGMENTS = ["working", "graduate", "switcher"] as const;

export async function OnboardingView() {
  const t = await getTranslations("profile");
  const result = await fetchMyProfile();
  return (
    <section>
      <StubBanner feature="F1 Skills profile intake" endpoint="GET /api/v1/profile/me" />
      <PageHeader title={t("onboardingTitle")} description={t("onboardingBody")} />
      {!result.ok ? <ApiError message={result.message} /> : null}
      <div className="grid gap-3 md:grid-cols-3">
        {SEGMENTS.map((segment) => (
          <Link key={segment} href="/app/profile">
            <Card className="h-full transition-colors hover:bg-accent">
              <CardHeader>
                <CardTitle>{t(`segment.${segment}`)}</CardTitle>
                {result.ok && result.data.segment === segment ? (
                  <Badge variant="secondary">{t("current")}</Badge>
                ) : null}
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
