import { DEFAULT_TARGET_ROLE, PathwayView } from "@/features/pathway";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  const roleId = firstParam(params.role) ?? DEFAULT_TARGET_ROLE;
  return <PathwayView roleId={roleId} scenario={parseScenario(params.scenario)} />;
}
