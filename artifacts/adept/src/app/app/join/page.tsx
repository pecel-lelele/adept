import { JoinView } from "@/features/core/components/JoinView";
import { firstParam, type SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  return <JoinView code={firstParam((await searchParams).code) ?? ""} />;
}
