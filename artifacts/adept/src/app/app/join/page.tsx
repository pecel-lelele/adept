import { asyncView } from "@/lib/next-compat/async-view";
import { JoinView } from "@/features/core/components/JoinView";
import { firstParam, type SearchParams } from "@/lib/scenario";

async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  return <JoinView code={firstParam((await searchParams).code) ?? ""} />;
}

export default asyncView(PageAsync);
