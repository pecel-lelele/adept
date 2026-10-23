import { asyncView } from "@/lib/next-compat/async-view";
import { CatalogueView, parseCatalogueQuery } from "@/features/pathway";
import { firstParam, type SearchParams } from "@/lib/scenario";

async function PageAsync({
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
      basePath="/app/courses"
      context={context}
    />
  );
}

export default asyncView(PageAsync);
