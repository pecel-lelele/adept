import { OrgDashboardView } from "@/features/org/components/OrgDashboardView";
import { parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  return <OrgDashboardView scenario={parseScenario((await searchParams).scenario)} />;
}
