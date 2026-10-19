import { RadarView } from "@/features/trends";
import { parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario } = await searchParams;
  return <RadarView scenario={parseScenario(scenario)} />;
}
