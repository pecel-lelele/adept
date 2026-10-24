import { ProfileView } from "@/features/profile";
import { parseScenario, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario } = await searchParams;
  return <ProfileView scenario={parseScenario(scenario)} />;
}
