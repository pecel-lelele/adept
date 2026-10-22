import { AssignedPackageView } from "@/features/org/components/AssignedPackageView";
import { CompareRolesView, PathwayView, savedRoleId } from "@/features/pathway";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const scenario = parseScenario(params.scenario);
  // Never assume a role: use the one in the link, else the learner's saved choice, else let
  // them compare and choose.
  const roleId = firstParam(params.role) ?? (await savedRoleId());
  const snapshotDate = firstParam(params.snapshot_date);
  if (!roleId)
    return <><AssignedPackageView /><CompareRolesView scenario={scenario} snapshotDate={snapshotDate} /></>;
  return (
    <><AssignedPackageView /><PathwayView
      roleId={roleId}
      scenario={scenario}
      snapshotDate={snapshotDate}
    /></>
  );
}
