import { asyncView } from "@/lib/next-compat/async-view";
import { SdgContributionView } from "@/features/sdg";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  return (
    <SdgContributionView roleId={firstParam(params.role)} scenario={parseScenario(params.scenario)} />
  );
}

export default asyncView(PageAsync);
