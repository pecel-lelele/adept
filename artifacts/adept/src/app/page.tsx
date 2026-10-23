import { asyncView } from "@/lib/next-compat/async-view";
import { LandingView } from "@/features/core";
import { firstParam, type SearchParams } from "@/lib/scenario";

async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const audience = firstParam((await searchParams).for) === "teams" ? "team" : "me";
  return <LandingView audience={audience} />;
}

export default asyncView(PageAsync);
