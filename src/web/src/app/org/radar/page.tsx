import { RadarView } from "@/features/trends";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario, snapshot_date } = await searchParams;
  return <RadarView scenario={parseScenario(scenario)} snapshotDate={firstParam(snapshot_date)} context="organisation" />;
}
