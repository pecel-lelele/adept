import { asyncView } from "@/lib/next-compat/async-view";
import { MatchDetailView } from "@/features/matching";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

async function PageAsync({
  params,
  searchParams,
}: {
  params: Promise<{ roleId: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const [{ roleId }, query] = await Promise.all([params, searchParams]);
  const scenario = parseScenario(query.scenario);
  const snapshotDate = firstParam(query.snapshot_date) || undefined;
  const sdgWeight = Math.min(1, Math.max(0, Number(firstParam(query.sdg)) || 0));
  return <MatchDetailView roleId={roleId} scenario={scenario} snapshotDate={snapshotDate} sdgWeight={sdgWeight} />;
}

export default asyncView(PageAsync);
