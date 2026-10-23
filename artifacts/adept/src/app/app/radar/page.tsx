import { asyncView } from "@/lib/next-compat/async-view";
import { RadarView } from "@/features/trends";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario, snapshot_date } = await searchParams;
  return <RadarView scenario={parseScenario(scenario)} snapshotDate={firstParam(snapshot_date)} />;
}

export default asyncView(PageAsync);
