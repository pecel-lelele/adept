import { asyncView } from "@/lib/next-compat/async-view";
import { MatchesView } from "@/features/matching";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario, snapshot_date, sdg } = await searchParams;
  const weight = Math.min(1, Math.max(0, Number(firstParam(sdg)) || 0));
  return (
    <MatchesView
      scenario={parseScenario(scenario)}
      snapshotDate={firstParam(snapshot_date) || undefined}
      sdgWeight={weight}
    />
  );
}

export default asyncView(PageAsync);
