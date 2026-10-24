import { SdgContributionView } from "@/features/sdg";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  return (
    <SdgContributionView roleId={firstParam(params.role)} scenario={parseScenario(params.scenario)} />
  );
}
