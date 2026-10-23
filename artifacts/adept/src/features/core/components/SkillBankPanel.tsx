import { asyncView } from "@/lib/next-compat/async-view";
import Link from "@/lib/next-compat/link";
import { ArrowUpRight, Layers3 } from "lucide-react";
import { getTranslations } from "@/lib/next-compat/intl";
import type { Schemas } from "@/lib/api";
import { skillName } from "@/lib/skill-bank";
import { journeyHref } from "@/lib/navigation";

async function SkillBankPanelAsync({skills,query}:{skills:Schemas["UserSkill"][];query:URLSearchParams}) {
  const t=await getTranslations("common.design");
  const render=(skill:Schemas["UserSkill"]) => <Link key={skill.skill_id} href={journeyHref("/app/courses?skill="+encodeURIComponent(skill.skill_id),query)} className="skill-bank-item"><span className="skill-bank-icon"><Layers3 size={17} strokeWidth={1.5}/></span><span><strong>{skillName(skill.skill_id)}</strong><small>{t("skillLevel",{level:skill.level})}</small></span><ArrowUpRight size={14} aria-hidden/></Link>;
  return <article className="insight-panel"><div className="panel-heading"><div><h2>{t("skillBank")}</h2><p className="panel-description">{t("skillBankBody")}</p></div><Link href={journeyHref("/app/profile",query)}>{t("review")} <ArrowUpRight size={13}/></Link></div>
    {skills.length ? <><div className="skill-bank-grid">{skills.slice(0,4).map(render)}</div>{skills.length>4 ? <details className="step-explanation"><summary>{t("moreSkills",{count:skills.length-4})}</summary><div className="skill-bank-grid">{skills.slice(4).map(render)}</div></details> : null}</> : <Link className="workspace-button subtle" href={journeyHref("/app/profile",query)}>{t("addSkills")}</Link>}
  </article>;
}

export const SkillBankPanel = asyncView(SkillBankPanelAsync);
