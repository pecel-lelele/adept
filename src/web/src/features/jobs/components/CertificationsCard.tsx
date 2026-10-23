import { Award, ArrowUpRight } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import { Fold } from "@/components/Fold";
import type { ScenarioId } from "@/lib/api";

import { fetchCertifications } from "../api";

/**
 * Optional certification exams for this role, folded to one line ("3 options from RM 205").
 * `payer`: the learner (personal plan) or the employer (team programme).
 */
export async function CertificationsCard({
  roleId,
  scenario,
  payer = "learner",
  max = 3,
  open = false,
}: {
  roleId: string;
  scenario: ScenarioId;
  payer?: "learner" | "employer";
  max?: number;
  open?: boolean;
}) {
  const t = await getTranslations("jobs");
  const result = await fetchCertifications(roleId, scenario, payer);
  if (!result.ok || !result.data.certifications.length) return null;
  const d = result.data;
  const rm = (n: number) => n.toLocaleString("en-MY", { maximumFractionDigits: 0 });
  const cheapest = Math.min(...d.certifications.map((c) => c.fee_myr));
  return (
    <Fold
      id="certifications"
      open={open}
      icon={<Award size={18} aria-hidden />}
      title={t("certs.title")}
      meta={t("certs.meta", { count: d.certifications.length, fee: rm(cheapest) })}
    >
      <p className="a-fold-text">{t(payer === "employer" ? "certs.payEmployer" : "certs.payLearner")}</p>
      <ul className="a-jobs">
        {d.certifications.slice(0, max).map((c) => (
          <li key={c.id} className="a-job">
            <div className="a-job-main">
              <a className="a-job-title" href={c.url} target="_blank" rel="noopener">
                {c.name}
                <ArrowUpRight size={14} aria-hidden />
              </a>
              <span className="a-job-where">
                {c.issuer}, {t(`certs.level.${c.level}`)}
              </span>
              {payer === "learner" && (c.prep_course_ids ?? []).length ? (
                <span className="a-job-good">{t("certs.prepared")}</span>
              ) : null}
            </div>
            <span className="a-job-fit" title={c.fee_note}>
              <strong>RM {rm(c.fee_myr)}</strong>
              <small>{c.exam_code}</small>
            </span>
          </li>
        ))}
      </ul>
      <div className="a-fold-foot">
        <MetaBar meta={d.meta} />
      </div>
    </Fold>
  );
}
