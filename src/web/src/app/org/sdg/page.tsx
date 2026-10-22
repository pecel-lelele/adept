import { OrgSdgView } from "@/features/sdg";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  return (
    <OrgSdgView
      region={firstParam(params.region)}
      role={firstParam(params.role) || undefined}
      scenario={parseScenario(params.scenario)}
    />
  );
}
