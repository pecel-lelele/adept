import { PlanView } from "@/features/org";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  return (
    <PlanView
      scenario={parseScenario(params.scenario)}
      roleId={firstParam(params.role)}
    />
  );
}
