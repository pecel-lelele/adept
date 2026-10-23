import { asyncView } from "@/lib/next-compat/async-view";
import { ProfileView } from "@/features/profile";
import { parseScenario, type SearchParams } from "@/lib/scenario";

async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario } = await searchParams;
  return <ProfileView scenario={parseScenario(scenario)} />;
}

export default asyncView(PageAsync);
