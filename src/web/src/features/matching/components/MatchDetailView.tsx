import { Circle, CircleCheck, CircleDashed, Leaf } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { MetaBar, PageHeader } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { scoreColour } from "@/components/viz";
import { RoleOpeningsCard } from "@/features/jobs";
import { RoleOutlookPanel } from "@/features/scenarios/components/RoleOutlookPanel";
import type { ScenarioId } from "@/lib/api";
import { savePlanAction } from "@/features/pathway/actions";
import { fetchPlanStatus } from "@/features/pathway/api";
import { ActionForm } from "@/features/pathway/components/ActionForm";

import { fetchMatch } from "../api";
import { MatchImprovements } from "./MatchImprovements";
import { MatchSdgTargets } from "./MatchSdgTargets";
import { ProfileNote } from "./ProfileNote";
import { CriticalOccupationBadge } from "./CriticalOccupationBadge";

/**
 * One role, in the same context as the list it was opened from (scenario, snapshot date and
 * UN Goals weight): fit and next action, then why (score parts), the gap, the outlook.
 */
export async function MatchDetailView({
  roleId,
  scenario,
  snapshotDate,
  sdgWeight = 0,
}: {
  roleId: string;
  scenario: ScenarioId;
  snapshotDate?: string;
  sdgWeight?: number;
}) {
  const t = await getTranslations("matching");
  const tp = await getTranslations("ui.page");
  const tsc = await getTranslations("scenarios");
  const [result, status] = await Promise.all([
    fetchMatch(roleId, scenario, snapshotDate, sdgWeight),
    fetchPlanStatus(),
  ]);
  const saved = status.ok ? status.data.saved : null;
  if (!result.ok) return (
    <div className="a-view">
      <PageHeader title={t("title")} description={t("description")} />
      <ErrorState failure={result} />
    </div>
  );
  const m = result.data;
  const pct = (m.score * 100).toFixed(1);
  const back =
    `/app/matches?scenario=${scenario}` +
    (snapshotDate ? `&snapshot_date=${encodeURIComponent(snapshotDate)}` : "") +
    (sdgWeight > 0 ? `&sdg=${sdgWeight.toFixed(2)}` : "");

  return (
    <div className="a-view">
      <PageHeader
        title={m.label}
        actions={
          <>
            {saved?.role_id === m.role_id ? (
              <Link className="a-btn" href={`/app/pathway?role=${encodeURIComponent(m.role_id)}&scenario=${saved.scenario}`}>
                {t("currentTarget")} · {t("openPlan")}
              </Link>
            ) : status.ok ? (
              <ActionForm action={savePlanAction} fields={{ role_id: m.role_id, scenario }} label={t("chooseRole")} />
            ) : (
              <p className="a-muted a-small" role="status">{t("planStatusUnavailable")}</p>
            )}
          </>
        }
      >
        <div className="a-chips">
          <Link className="a-chip" href={back}>
            ← {tp("backToRoles")}
          </Link>
          {sdgWeight > 0 ? (
            <span className="a-chip" data-tone="up">
              <Leaf size={12} aria-hidden /> {tp("sdgWeighted", { weight: Math.round(sdgWeight * 100) })}
            </span>
          ) : null}
          <MetaBar meta={m.meta} />
        </div>
      </PageHeader>
      <ProfileNote note={m.profile_note} />
      <CriticalOccupationBadge badge={m.critical_occupation} />
      <div className="a-split">
        <section className="a-card" aria-labelledby="h-raise">
          <div className="a-card-head">
            <h2 id="h-raise">{t("improvementsTitle")}</h2>
            <span className="a-fit is-inline" style={{ color: scoreColour(m.score) }} role="img" aria-label={`${pct}% ${tp("fit")}`}>
              <strong>{pct}%</strong>
            </span>
          </div>
          <MatchImprovements items={m.improvements ?? []} hideTitle fallback={t("raiseFallback")} />
        </section>

        <aside className="a-aside">
          <section className="a-card" aria-labelledby="h-gap">
            <div className="a-card-head">
              <h2 id="h-gap">{tp("gapTitle")}</h2>
            </div>
            {m.missing_skills.length || m.partial_skills.length ? (
              <ul className="a-gaplist">
                {m.missing_skills.map((s) => (
                  <li key={s.id}>
                    <Circle size={11} aria-hidden data-tone="down" /> {s.label}
                    <span className="a-chip" data-tone="down">{t("missing")}</span>
                  </li>
                ))}
                {m.partial_skills.map((s) => (
                  <li key={s.id}>
                    <CircleDashed size={11} aria-hidden data-tone="warn" /> {s.label}
                    <span className="a-chip" data-tone="warn">{t("partial")}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="a-muted a-small a-inline">
                <CircleCheck size={14} aria-hidden /> {tp("noGap")}
              </p>
            )}
          </section>
          {m.sdg_targets.length ? (
            <section className="a-card" aria-labelledby="h-goals">
              <div className="a-card-head">
                <h2 id="h-goals">{tp("goals")}</h2>
              </div>
              <MatchSdgTargets targets={m.sdg_targets} />
            </section>
          ) : null}
        </aside>
      </div>

      <RoleOpeningsCard roleId={m.role_id} scenario={scenario} limit={5} malaysiaFocus />

      <section className="a-card" aria-labelledby="h-outlook">
        <div className="a-card-head">
          <h2 id="h-outlook">{tsc("outlook")}</h2>
        </div>
        <p className="a-card-sub">{tp("outlookHint")}</p>
        <RoleOutlookPanel roleId={m.role_id} scenario={scenario} snapshotDate={snapshotDate} />
      </section>
      {m.data_provenance_note ? (
        <p className="a-small a-muted">
          {t("provenance")}: {m.data_provenance_note}
        </p>
      ) : null}
    </div>
  );
}
