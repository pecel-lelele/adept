import { getTranslations } from "next-intl/server";
import { BookOpen, ArrowUpRight } from "lucide-react";
import { SdgBadge } from "@/components";
import type { Schemas } from "@/lib/api";
async function CourseLine({ course }: { course: Schemas["Course"] }) {
  const t = await getTranslations("pathway");
  return <div className="pathway-course"><BookOpen size={19} strokeWidth={1.5}/><div><a href={course.url} target="_blank" rel="noreferrer">{course.title} <ArrowUpRight size={12} className="inline" aria-hidden/></a><p>{course.provider} · {t("hours",{hours:course.hours})}</p></div><span>{course.cost_myr === 0 ? t("free") : t("cost",{amount:course.cost_myr})}</span></div>;
}
export async function PathwaySteps({ steps, memberNames }: { steps: Schemas["PathwayStep"][]; memberNames?: Record<string,string> }) {
  const t = await getTranslations("pathway"), d = await getTranslations("common.design");
  const label = (id:string) => steps.find(s=>s.skill_id===id)?.skill_label || id;
  return <ol className="pathway-timeline">{steps.map(step => <li key={step.order}>
    <span className="step-number">{step.order}</span><article className="pathway-step">
      <header><h2>{step.skill_label || step.skill_id}</h2><small>{t("weeks",{start:step.week_start,end:step.week_end})} · {t("hours",{hours:step.est_hours})}</small></header>
      {step.courses.map(c=><CourseLine key={c.id} course={c}/>)}
      <details className="step-explanation"><summary>{d("stepDetails")}</summary><div>
        <p>{step.reason}</p>
        <p>{t("step.levels",{current:step.current_level ?? 0,reaches:step.reaches_level ?? 0,target:step.target_level ?? 1})}</p>
        {step.prerequisites?.length ? <p>{t("step.prerequisites",{skills:step.prerequisites.map(label).join(", ")})}</p> : null}
        {step.courses.map(c=><p key={c.id}>{c.source?.name} · {t("verified",{date:c.verified_at})}{c.hrd_claimable ? " · "+t("hrdClaimable") : ""}{c.price_note ? " · "+c.price_note : ""}{c.hrd_note ? " · "+c.hrd_note : ""}{c.duration_note ? " · "+c.duration_note : ""}</p>)}
        <div className="flex flex-wrap gap-1">{step.sdg_targets?.map(s=><SdgBadge key={s.target} target={s}/>)}</div>
        {memberNames && step.member_ids?.length ? <p>{t("step.members",{count:step.member_ids.length,members:step.member_ids.map(id=>memberNames[id]??id).join(", ")})}</p> : null}
      </div></details>
      {step.alternatives?.length ? <details className="step-explanation"><summary>{t("step.alternatives",{count:step.alternatives.length})}</summary>{step.alternatives.map(c=><CourseLine key={c.id} course={c}/>)}</details> : null}
    </article></li>)}</ol>;
}
