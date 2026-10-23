import { asyncView } from "@/lib/next-compat/async-view";
import { PlanView } from "@/features/org";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

async function PageAsync({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  return (
    <PlanView
      scenario={parseScenario(params.scenario)}
      roleId={firstParam(params.role)}
      memberIds={params.cohort ? (Array.isArray(params.member) ? params.member : params.member ? [params.member] : []) : undefined}
    />
  );
}

export default asyncView(PageAsync);
