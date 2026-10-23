import { asyncView } from "@/lib/next-compat/async-view";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { getTranslations } from "@/lib/next-compat/intl";

import type { Schemas } from "@/lib/api";

/** Trend replay, "what changed and why": each role's rank move between two snapshots and the
 *  skills whose trend moved it most. */
async function ReplayChangesAsync({ data }: { data: Schemas["ReplayResponse"] }) {
  const t = await getTranslations("matching.changes");
  return (
    <section className="a-card a-replay" aria-labelledby="replay-title">
      <div className="a-card-head">
        <h2 id="replay-title">{t("title", { from: data.from_date, to: data.to_date })}</h2>
      </div>
      <ol className="a-replay-list">
        {data.movements.map((m) => {
          const delta = m.rank_before - m.rank_after;
          const Icon = delta > 0 ? ArrowUp : delta < 0 ? ArrowDown : Minus;
          const tone = delta > 0 ? "up" : delta < 0 ? "down" : undefined;
          return (
            <li key={m.role_id}>
              <span className="a-replay-rank" data-tone={tone}>
                <Icon size={14} aria-hidden />
                {delta === 0 ? t("same") : t(delta > 0 ? "up" : "down", { count: Math.abs(delta) })}
              </span>
              <div className="a-replay-main">
                <strong>
                  #{m.rank_after} {m.label}
                </strong>
                <small>{t("rankWas", { rank: m.rank_before })}</small>
                {m.drivers.length ? (
                  <div className="a-chips">
                    <span className="a-small a-muted">{t("because")}</span>
                    {m.drivers.map((d) => (
                      <span key={d.skill_id} className="a-chip" data-tone={d.effect > 0 ? "up" : "down"}>
                        {d.label} {d.effect > 0 ? t("rose") : t("fell")}
                      </span>
                    ))}
                  </div>
                ) : (
                  <small className="a-muted">{t("noDrivers")}</small>
                )}
              </div>
            </li>
          );
        })}
      </ol>
      <p className="a-small a-muted" style={{ margin: 0 }}>
        {t("note")}
      </p>
    </section>
  );
}

export const ReplayChanges = asyncView(ReplayChangesAsync);
