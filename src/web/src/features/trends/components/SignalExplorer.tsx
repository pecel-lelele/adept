"use client";
import { useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import type { ScenarioId, Schemas } from "@/lib/api";
export function SignalExplorer({items,scenario,dates,date}:{items:Schemas["SkillVelocity"][];scenario:ScenarioId;dates:string[];date:string}) {
  const t=useTranslations("common.design"),router=useRouter(),pathname=usePathname(),params=useSearchParams();
  const [search,setSearch]=useState(""),[direction,setDirection]=useState("all"),[pending,startTransition]=useTransition();
  const key=scenario==="fast" ? "direction_fast" : "direction_moderate";
  const velocity=scenario==="fast" ? "velocity_fast" : "velocity_moderate";
  const visible=items.filter(i=>i.skill_label.toLowerCase().includes(search.toLowerCase()) && (direction==="all"||i[key]===direction)).sort((a,b)=>b[velocity]-a[velocity]);
  return <div aria-busy={pending}>
    <div className="radar-counts">{(["rising","stable","declining"] as const).map(d=><div key={d}><span className="workspace-eyebrow">{t(d)}</span><strong>{items.filter(i=>i[key]===d).length}</strong></div>)}</div>
    <div className="radar-tools">
      <input aria-label={t("search")} placeholder={t("search")} value={search} onChange={e=>setSearch(e.target.value)}/>
      <select aria-label={t("filters")} value={direction} onChange={e=>setDirection(e.target.value)}><option value="all">{t("all")}</option>{(["rising","stable","declining"] as const).map(d=><option key={d} value={d}>{t(d)}</option>)}</select>
      <label>{t("snapshot")}<select value={date} disabled={pending} onChange={e=>{const next=new URLSearchParams(params);next.set("snapshot_date",e.target.value);startTransition(()=>router.push(pathname+"?"+next.toString(),{scroll:false}));}}>{dates.map(d=><option key={d} value={d}>{d}</option>)}</select></label>
    </div>
    <div className="signal-list">{visible.map(i=><details className="signal-row" key={i.skill_id}><summary><span>{i.skill_label}</span><span className="signal-meter" aria-hidden><i style={{width:Math.min(100,Math.abs(i[velocity])*50)+"%"}}/></span><span className="signal-direction">{t(i[key])} {i[key]==="rising"?"↗":i[key]==="declining"?"↘":"→"}</span></summary><p>{i.labor_decay_source_note}</p></details>)}</div>
    {!visible.length ? <p className="activity-note">No skills match these filters.</p> : null}
  </div>;
}
