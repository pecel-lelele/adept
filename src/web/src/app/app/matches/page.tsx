import { MatchesView } from "@/features/matching";
import { parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario } = await searchParams;
  return <MatchesView scenario={parseScenario(scenario)} />;
}
