import { asyncView } from "@/lib/next-compat/async-view";
import { GapsView } from "@/features/org";
import { parseScenario, type SearchParams } from "@/lib/scenario";

async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario } = await searchParams;
  return <GapsView scenario={parseScenario(scenario)} />;
}

export default asyncView(PageAsync);
