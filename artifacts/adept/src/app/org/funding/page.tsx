import { asyncView } from "@/lib/next-compat/async-view";
import { FundingView } from "@/features/org/components/FundingView";
import { fundingYear } from "@/features/org/funding-year";
import { firstParam, type SearchParams } from "@/lib/scenario";

async function PageAsync({ searchParams }: { searchParams: Promise<SearchParams> }) {
  return <FundingView year={fundingYear(firstParam((await searchParams).year))} />;
}

export default asyncView(PageAsync);
