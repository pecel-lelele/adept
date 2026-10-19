import { getTranslations } from "next-intl/server";

import { Badge, Card, CardContent, CardHeader, CardTitle } from "@/components";
import type { Schemas } from "@/lib/api";

export async function PathwaySteps({ steps }: { steps: Schemas["PathwayStep"][] }) {
  const t = await getTranslations("pathway");
  return (
    <ol className="space-y-3">
      {steps.map((step) => (
        <li key={step.order}>
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>
                {step.order}. {step.skill_id}
              </CardTitle>
              <span className="text-xs text-muted-foreground">
                {t("weeks", { start: step.week_start, end: step.week_end })} ·{" "}
                {t("hours", { hours: step.est_hours })}
              </span>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p className="text-muted-foreground">{step.reason}</p>
              {step.courses.map((c) => (
                <div key={c.id} className="flex flex-wrap items-center gap-2">
                  <a href={c.url} className="underline" target="_blank" rel="noreferrer">
                    {c.title}
                  </a>
                  <span className="text-xs text-muted-foreground">{c.provider}</span>
                  <Badge variant="outline">
                    {c.cost_myr === 0 ? t("free") : t("cost", { amount: c.cost_myr })}
                  </Badge>
                  {c.hrd_claimable ? <Badge variant="success">{t("hrdClaimable")}</Badge> : null}
                  <span className="text-xs text-muted-foreground">
                    {t("verified", { date: c.verified_at })}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </li>
      ))}
    </ol>
  );
}
