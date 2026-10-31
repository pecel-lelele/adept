import { useTranslations } from "next-intl";

import type { Schemas } from "@/lib/api";

type Provenance = Partial<Pick<Schemas["TrendSnapshotMeta"],
  "is_replay" | "observation_window_start" | "observation_window_end" |
  "retrieved_at" | "retrieved_at_basis"
>> & { snapshot_date: string };

/** Replay origin survives fixture → PostgreSQL; storage origin never decides this label. */
export function TrendProvenanceNotice({ meta }: { meta: Provenance }) {
  const t = useTranslations("common.freshness");
  if (meta.is_replay === undefined) return null;
  const window = meta.observation_window_start && meta.observation_window_end;
  return (
    <div className="a-notice" role="note" data-trend-replay={meta.is_replay === true ? "true" : undefined}>
      <p>{meta.is_replay === true && window ? t("replay", {
        from: meta.observation_window_start!, to: meta.observation_window_end!, date: meta.snapshot_date,
      }) : meta.is_replay === null || !window ? t("unverified", { date: meta.snapshot_date }) : t("observed", {
        from: meta.observation_window_start!, to: meta.observation_window_end!,
      })}</p>
      {meta.retrieved_at_basis === "git_commit_date" && meta.retrieved_at ?
        <p>{t("commitDerived", { date: meta.retrieved_at })}</p> : null}
    </div>
  );
}
