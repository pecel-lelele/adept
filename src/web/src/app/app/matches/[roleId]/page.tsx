import { MatchDetailView } from "@/features/matching";
import { RoleOutlookPanel } from "@/features/scenarios";
import { parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ roleId: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const [{ roleId }, query] = await Promise.all([params, searchParams]);
  const scenario = parseScenario(query.scenario);
  return (
    <div className="space-y-4">
      <MatchDetailView roleId={roleId} scenario={scenario} />
      <RoleOutlookPanel roleId={roleId} scenario={scenario} />
    </div>
  );
}
