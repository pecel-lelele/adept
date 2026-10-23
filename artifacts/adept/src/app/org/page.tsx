import { asyncView } from "@/lib/next-compat/async-view";
import { OrgDashboardView } from "@/features/org/components/OrgDashboardView";
import { parseScenario, type SearchParams } from "@/lib/scenario";

async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  return <OrgDashboardView scenario={parseScenario((await searchParams).scenario)} />;
}

export default asyncView(PageAsync);
