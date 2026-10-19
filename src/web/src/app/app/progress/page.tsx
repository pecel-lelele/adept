import { DEFAULT_TARGET_ROLE, ProgressView } from "@/features/pathway";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  const roleId = firstParam(params.role) ?? DEFAULT_TARGET_ROLE;
  return <ProgressView roleId={roleId} scenario={parseScenario(params.scenario)} />;
}
