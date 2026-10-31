import { RadarView } from "@/features/trends";
import { parseTrendRange } from "@/features/trends/range";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  return <RadarView scenario={parseScenario(params.scenario)} snapshotDate={firstParam(params.snapshot_date)} context="organisation" range={parseTrendRange(params)} />;
}
