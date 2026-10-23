import { asyncView } from "@/lib/next-compat/async-view";
import { Award, BriefcaseBusiness } from "lucide-react";
import Link from "@/lib/next-compat/link";
import { getTranslations } from "@/lib/next-compat/intl";
import type { ReactNode } from "react";

import type { ScenarioId, Schemas } from "@/lib/api";

import { fetchCertifications, fetchRoleOpenings } from "../api";

function Tile({ icon, label, value, sub, href }: { icon: ReactNode; label: string; value: string; sub: string; href?: string }) {
  const body = (
    <>
      <span className="a-tile-label">
        {icon} {label}
      </span>
      <strong className="a-tile-value">{value}</strong>
      <span className="a-tile-sub">{sub}</span>
    </>
  );
  return href ? (
    <Link className="a-tile is-link" href={href}>
      {body}
    </Link>
  ) : (
    <div className="a-tile">{body}</div>
  );
}

/**
 * What the plan leads to, beside the plan's own time and cost: the cheapest relevant
 * certification exam and current job openings for the role.
 */
async function CareerRoadmapAsync({ plan, scenario }: { plan: Schemas["Pathway"]; scenario: ScenarioId }) {
  const t = await getTranslations("jobs.roadmap");
  const [openings, certs] = await Promise.all([
    fetchRoleOpenings(plan.role_id, scenario),
    fetchCertifications(plan.role_id, scenario),
  ]);
  const cert = certs.ok ? certs.data.certifications[0] : undefined;
  const o = openings.ok ? openings.data : undefined;
  const rm = (n: number) => n.toLocaleString("en-MY", { maximumFractionDigits: 0 });
  return (
    <section className="a-tiles" aria-label={t("title")}>
      <Tile
        icon={<Award size={15} aria-hidden />}
        label={t("prove")}
        value={cert ? cert.exam_code : "—"}
        sub={cert ? t("proveSub", { fee: rm(cert.fee_myr) }) : t("proveNone")}
        href={cert ? "#certifications" : undefined}
      />
      <Tile
        icon={<BriefcaseBusiness size={15} aria-hidden />}
        label={t("apply")}
        value={String(o?.open_count ?? 0)}
        sub={
          o && o.open_count
            ? o.rated
              ? t("applySub", { after: o.ready_after_plan, now: o.ready_now })
              : t("applyCount")
            : t("applyNone")
        }
        href={o && o.open_count ? "#openings" : undefined}
      />
    </section>
  );
}

export const CareerRoadmap = asyncView(CareerRoadmapAsync);
