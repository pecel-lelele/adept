import { MatchDetailView } from "@/features/matching";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ roleId: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const [{ roleId }, query] = await Promise.all([params, searchParams]);
  const scenario = parseScenario(query.scenario);
  const snapshotDate = firstParam(query.snapshot_date) || undefined;
  return <MatchDetailView roleId={roleId} scenario={scenario} snapshotDate={snapshotDate} />;
}
