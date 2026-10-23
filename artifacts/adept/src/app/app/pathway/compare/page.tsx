import { asyncView } from "@/lib/next-compat/async-view";
import { CompareRolesView } from "@/features/pathway";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

async function PageAsync({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const roles = params.roles;
  const roleIds = (
    Array.isArray(roles) ? roles : roles ? roles.split(",") : []
  ).filter(Boolean);
  return (
    <CompareRolesView
      scenario={parseScenario(params.scenario)}
      roleIds={roleIds}
      snapshotDate={firstParam(params.snapshot_date)}
    />
  );
}

export default asyncView(PageAsync);
