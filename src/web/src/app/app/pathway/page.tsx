import { redirect } from "next/navigation";
import { ErrorState } from "@/components";
import { fetchPlanStatus, PathwayView } from "@/features/pathway";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const scenario = parseScenario(params.scenario);
  // A URL role is a preview selector, not a saved choice. Unlock after an explicit save.
  // A failed check says nothing about the choice, so it must not ask the learner to choose again.
  const status = await fetchPlanStatus();
  if (!status.ok) return <ErrorState failure={status} />;
  const chosen = status.data.saved?.role_id;
  const roleId = chosen ? firstParam(params.role) || chosen : null;
  const snapshotDate = firstParam(params.snapshot_date);
  if (!roleId)
    redirect(`/app/matches?scenario=${scenario}&choose_role=1${snapshotDate ? `&snapshot_date=${encodeURIComponent(snapshotDate)}` : ""}`);
  return (
    <><PathwayView
      roleId={roleId}
      scenario={scenario}
      snapshotDate={snapshotDate}
    /></>
  );
}
