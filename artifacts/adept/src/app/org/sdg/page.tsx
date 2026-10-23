import { asyncView } from "@/lib/next-compat/async-view";
import { OrgSdgView } from "@/features/sdg";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  return (
    <OrgSdgView
      region={firstParam(params.region)}
      role={firstParam(params.role) || undefined}
      scenario={parseScenario(params.scenario)}
    />
  );
}

export default asyncView(PageAsync);
