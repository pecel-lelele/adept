import { asyncView } from "@/lib/next-compat/async-view";
import Link from "@/lib/next-compat/link";
import { getTranslations } from "@/lib/next-compat/intl";

import { ApiError, EmptyState, PageHeader } from "@/components";
import { byStatus, fetchMyProgrammes } from "@/features/org/work/api";
import { workOrg } from "@/features/org/work/org";
import { ProgressView } from "@/features/pathway";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

/** Progress on an accepted programme (organisation scope: HR reviews what is recorded here). */
async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  const [org, mine, t] = await Promise.all([workOrg(), fetchMyProgrammes(), getTranslations("org.work")]);
  if (!mine.ok) return <ApiError message={mine.message} />;
  const accepted = mine.ok ? byStatus(mine.data.assignments).accepted : [];
  const roles = [...new Map(accepted.map((a) => [a.agreement.role_id, a])).values()];
  const wanted = firstParam(params.role);
  const current = roles.find((a) => a.agreement.role_id === wanted) ?? roles[0];
  if (!current) {
    return (
      <div className="a-view">
        <PageHeader eyebrow={org.name} title={t("progressTitle")} />
        <EmptyState
          title={t("noAccepted")}
          description={t("noAcceptedHint")}
          action={
            <Link className="a-btn" href="/work/plan">
              {t("reviewAgreement")}
            </Link>
          }
        />
      </div>
    );
  }
  return (
    <>
      {roles.length > 1 ? (
        <nav className="a-progtabs" aria-label={t("programmesNav")}>
          {roles.map((a) => (
            <Link
              key={a.agreement.role_id}
              href={`/work/progress?role=${encodeURIComponent(a.agreement.role_id)}`}
              aria-current={a === current ? "page" : undefined}
            >
              {a.agreement.title}
            </Link>
          ))}
        </nav>
      ) : null}
      <ProgressView roleId={current.agreement.role_id} scenario={parseScenario(params.scenario)} orgName={org.name} />
    </>
  );
}

export default asyncView(PageAsync);
