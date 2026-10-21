import { MatchesView } from "@/features/matching";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario, snapshot_date } = await searchParams;
  return <MatchesView scenario={parseScenario(scenario)} snapshotDate={firstParam(snapshot_date) || undefined} />;
}
