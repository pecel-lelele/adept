import { LandingView } from "@/features/core";
import { firstParam, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const audience = firstParam((await searchParams).for) === "teams" ? "team" : "me";
  return <LandingView audience={audience} />;
}
