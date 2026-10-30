import { FundingView } from "@/features/org/components/FundingView";
import { fundingYear } from "@/features/org/funding-year";
import { firstParam, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  const plan = new URLSearchParams();
  for (const key of ["scenario", "role", "cohort", "member"]) {
    const values = params[key];
    for (const value of Array.isArray(values) ? values : values ? [values] : []) plan.append(key, value);
  }
  return <FundingView year={fundingYear(firstParam(params.year))} planQuery={plan.toString()} />;
}
