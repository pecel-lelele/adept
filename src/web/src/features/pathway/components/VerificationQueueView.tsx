import { ArrowUpRight, CircleCheck, ClipboardCheck, Inbox } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { Badge, EmptyState, ErrorState, Kpis, PageHeader } from "@/components";
import { call, getApi } from "@/lib/api";

import { reviewCompletionAction } from "../actions";
import { EvidenceBadge } from "./EvidenceBadge";
import { ReviewForm } from "./ReviewForm";

/** HR (company) or career advisor (institution): review members' course completions. */
export async function VerificationQueueView() {
  const t = await getTranslations("pathway");
  const tp = await getTranslations("ui.page");
  const api = await getApi();
  const result = await call(api.GET("/api/v1/pathway/verifications"));
  return (
    <div className="a-view">
      <PageHeader
        title={t("verify.title")}
        description={t("verify.description")}
        actions={
          <Link href="/org/courses" className="a-btn is-ghost is-small">
            {t("catalogue.browse")}
          </Link>
        }
      />
      <p className="a-notice" data-tone="info">
        {t("verify.hrdHint")}
      </p>
      {!result.ok ? (
        <ErrorState failure={result} />
      ) : result.data.items.length === 0 ? (
        <EmptyState title={t("verify.empty")} />
      ) : (
        <>
          <Kpis
            items={[
              {
                label: tp("kPending"),
                value: result.data.pending,
                icon: <ClipboardCheck size={15} />,
                tone: result.data.pending ? "warn" : "up",
              },
              { label: tp("kReviewedDone"), value: result.data.items.length - result.data.pending, icon: <CircleCheck size={15} /> },
              { label: tp("kSubmitted"), value: result.data.items.length, icon: <Inbox size={15} /> },
            ]}
          />
          <ul className="a-reviews">
            {result.data.items.map((item) => {
              const ev = item.evidence;
              const reviewed = ev?.kind === "org_confirmed" || ev?.kind === "org_rejected";
              return (
                <li
                  key={`${item.user_id}-${item.role_id}-${item.course.id}`}
                  className="a-card a-review"
                  data-reviewed={reviewed || undefined}
                >
                  <div className="a-review-who">
                    <span className="a-avatar" aria-hidden>
                      {item.display_name.slice(0, 2).toUpperCase()}
                    </span>
                    <div>
                      <strong>{item.display_name}</strong>
                      <small>{t("verify.forRole", { role: item.role_id })}</small>
                    </div>
                    <EvidenceBadge evidence={ev ?? null} />
                  </div>
                  <div className="a-review-course">
                    <a href={item.course.url} target="_blank" rel="noreferrer" className="a-link">
                      {item.course.title} <ArrowUpRight size={13} aria-hidden />
                    </a>
                    <span className="a-small a-muted">{item.course.provider}</span>
                    {item.course.hrd_claimable ? <Badge variant="success">{t("hrdClaimable")}</Badge> : null}
                  </div>
                  {ev?.url ? (
                    <p className="a-small" style={{ margin: 0 }}>
                      <a href={ev.url} target="_blank" rel="noreferrer" className="a-link">
                        {t("verify.openProof")}
                      </a>{" "}
                      <span className="a-muted">({t("verify.checkName")})</span>
                    </p>
                  ) : null}
                  {reviewed && ev?.review_note ? (
                    <p className="a-small a-muted" style={{ margin: 0 }}>
                      {t("evidence.reviewNote", { note: ev.review_note })}
                    </p>
                  ) : null}
                  <ReviewForm
                    action={reviewCompletionAction}
                    fields={{
                      workspace: result.data.org_id,
                      user_id: item.user_id,
                      role_id: item.role_id,
                      course_id: item.course.id,
                      submitted_at: ev?.submitted_at ?? "",
                    }}
                  />
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
