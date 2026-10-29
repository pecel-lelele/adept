import { useTranslations } from "next-intl";

import { SdgTiles } from "@/components/viz";
import type { Schemas } from "@/lib/api";

export function MatchSdgTargets({ targets }: { targets: Schemas["SdgTarget"][] }) {
  const t = useTranslations("sdg");
  const goals = [...new Set(targets.map((target) => target.goal))].map((goal) => {
    const links = targets.filter((target) => target.goal === goal);
    const reason = links.map((link) => link.reason).filter(Boolean).join(" ");
    return {
      goal, reason,
      title: links.map((link) => `${link.target} ${link.label}. ${link.reason ?? ""}${link.strength ? ` (${t(link.strength)})` : ""}`).join(" "),
    };
  });
  return <SdgTiles goals={goals} />;
}
