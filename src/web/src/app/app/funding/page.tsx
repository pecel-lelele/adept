import { FundingView } from "@/features/org/components/FundingView";
import { fundingYear } from "@/features/org/funding-year";
import { firstParam, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  return <FundingView year={fundingYear(firstParam((await searchParams).year))} />;
}
