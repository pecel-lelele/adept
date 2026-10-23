import { GapsView } from "@/features/org";
import { parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario } = await searchParams;
  return <GapsView scenario={parseScenario(scenario)} />;
}
