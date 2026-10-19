import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageHeader,
  StubBanner,
} from "@/components";

import { fetchMyProfile } from "../api";

export async function ProfileView() {
  const t = await getTranslations("profile");
  const result = await fetchMyProfile();
  if (!result.ok) return <ApiError message={result.message} />;
  const p = result.data;

  return (
    <section>
      <StubBanner feature="F1 Skills profile intake" endpoint="GET /api/v1/profile/me" />
      <PageHeader title={t("title")} description={`${p.display_name} · ${t(`segment.${p.segment}`)}`}>
        <div className="flex flex-wrap gap-2 pt-1 text-sm">
          <Badge variant="outline">{t("hoursPerWeek", { hours: p.hours_per_week })}</Badge>
          <Badge variant="outline">{t("budget", { amount: p.budget_myr })}</Badge>
          {p.hrd_eligible ? <Badge variant="success">{t("hrdEligible")}</Badge> : null}
        </div>
      </PageHeader>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("skills")}</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {p.skills.map((s) => (
                <li key={s.skill_id} className="flex justify-between">
                  <span>{s.skill_id}</span>
                  <span className="text-muted-foreground">
                    {t("level", { level: s.level })} · {s.source}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("interests")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-1">
              {(p.interests ?? []).map((i) => (
                <Badge key={i} variant="secondary">
                  {i}
                </Badge>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">{t("cvNote")}</p>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
