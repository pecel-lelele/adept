import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ApiError, Badge, Card, CardContent, PageHeader } from "@/components";
import { call, getApi } from "@/lib/api";

import { reviewCompletionAction } from "../actions";
import { EvidenceBadge } from "./EvidenceBadge";
import { ReviewForm } from "./ReviewForm";

/** HR (company) or career advisor (institution): review members' course completions. */
export async function VerificationQueueView() {
  const t = await getTranslations("pathway");
  const api = await getApi();
  const result = await call(api.GET("/api/v1/pathway/verifications"));
  return (
    <section className="space-y-4">
      <PageHeader title={t("verify.title")} description={t("verify.description")} />
      <p className="text-xs text-muted-foreground">{t("verify.hrdHint")}</p>
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : result.data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("verify.empty")}</p>
      ) : (
        <>
          <p className="text-sm">{t("verify.pending", { count: result.data.pending })}</p>
          <ul className="space-y-3">
            {result.data.items.map((item) => {
              const ev = item.evidence;
              const reviewed = ev?.kind === "org_confirmed" || ev?.kind === "org_rejected";
              return (
                <li key={`${item.user_id}-${item.role_id}-${item.course.id}`}>
                  <Card>
                    <CardContent className="space-y-2 pt-4 text-sm">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <span className="font-medium">{item.display_name}</span>
                        <span className="text-xs text-muted-foreground">
                          {t("verify.forRole", { role: item.role_id })}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <a href={item.course.url} target="_blank" rel="noreferrer" className="underline">
                          {item.course.title}
                        </a>
                        <span className="text-xs text-muted-foreground">{item.course.provider}</span>
                        {item.course.hrd_claimable ? (
                          <Badge variant="success">{t("hrdClaimable")}</Badge>
                        ) : null}
                      </div>
                      <EvidenceBadge evidence={ev ?? null} />
                      {ev?.url ? (
                        <p className="text-xs">
                          <a href={ev.url} target="_blank" rel="noreferrer" className="underline">
                            {t("verify.openProof")}
                          </a>{" "}
                          <span className="text-muted-foreground">({t("verify.checkName")})</span>
                        </p>
                      ) : null}
                      {reviewed && ev?.review_note ? (
                        <p className="text-xs text-muted-foreground">
                          {t("evidence.reviewNote", { note: ev.review_note })}
                        </p>
                      ) : null}
                      <ReviewForm
                        action={reviewCompletionAction}
                        fields={{
                          user_id: item.user_id,
                          role_id: item.role_id,
                          course_id: item.course.id,
                        }}
                      />
                    </CardContent>
                  </Card>
                </li>
              );
            })}
          </ul>
        </>
      )}
      <Link href="/org/courses" className="text-sm underline">
        {t("catalogue.browse")}
      </Link>
    </section>
  );
}
