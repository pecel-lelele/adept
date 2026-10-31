import { redirect } from "next/navigation";
import { ErrorState } from "@/components";
import { fetchPlanStatus, ProgressView } from "@/features/pathway";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  const scenario = parseScenario(params.scenario);
  const status = await fetchPlanStatus();
  if (!status.ok) return <ErrorState failure={status} />;
  const chosen = status.data.saved?.role_id;
  const roleId = chosen ? firstParam(params.role) || chosen : null;
  if (!roleId) redirect(`/app/matches?scenario=${scenario}&choose_role=1`);
  return <ProgressView roleId={roleId} scenario={scenario} />;
}
