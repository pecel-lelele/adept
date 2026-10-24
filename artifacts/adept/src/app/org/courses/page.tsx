import { CatalogueView, parseCatalogueQuery } from "@/features/pathway";
import { firstParam, type SearchParams } from "@/lib/scenario";

/** HR / career-centre view of the same catalogue (corporate bundles, HRD Corp-claimable). */
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const context = Object.fromEntries(
    ["role", "scenario", "snapshot_date"].flatMap((key) => {
      const value = firstParam(params[key]);
      return value ? [[key, value]] : [];
    }),
  );
  return (
    <CatalogueView
      query={parseCatalogueQuery(params)}
      basePath="/org/courses"
      context={context}
    />
  );
}
