import { RadarView } from "@/features/trends";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario, snapshot_date, from, to, skill } = await searchParams;
  const skillIds = (Array.isArray(skill) ? skill : skill ? [skill] : []).filter(Boolean);
  return <RadarView scenario={parseScenario(scenario)} snapshotDate={firstParam(snapshot_date)}
      range={{ from: firstParam(from) || undefined, to: firstParam(to) || undefined, skillIds }}
    />;
}
