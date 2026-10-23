import { DashboardView } from "@/features/core/components/DashboardView";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  const query = new URLSearchParams(
    Object.entries(params).flatMap(([key, value]) => {
      const item = firstParam(value);
      return item ? [[key, item]] : [];
    }),
  );
  return <DashboardView scenario={parseScenario(params.scenario)} query={query} />;
}
