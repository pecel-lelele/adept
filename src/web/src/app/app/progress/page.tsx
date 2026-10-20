import { CompareRolesView, ProgressView, savedRoleId } from "@/features/pathway";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  const scenario = parseScenario(params.scenario);
  const roleId = firstParam(params.role) ?? (await savedRoleId());
  if (!roleId) return <CompareRolesView scenario={scenario} />;
  return <ProgressView roleId={roleId} scenario={scenario} />;
}
