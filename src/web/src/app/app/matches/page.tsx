import { MatchesView } from "@/features/matching";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario, snapshot_date, sdg, choose_role } = await searchParams;
  const weight = Math.min(1, Math.max(0, Number(firstParam(sdg)) || 0));
  return (
    <MatchesView
      scenario={parseScenario(scenario)}
      snapshotDate={firstParam(snapshot_date) || undefined}
      sdgWeight={weight}
      chooseRoleFirst={firstParam(choose_role) === "1"}
    />
  );
}
