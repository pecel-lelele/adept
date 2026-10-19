import { CatalogueView, parseCatalogueQuery } from "@/features/pathway";
import type { SearchParams } from "@/lib/scenario";

/** HR / career-centre view of the same catalogue (corporate bundles, HRD Corp-claimable). */
export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  return <CatalogueView query={parseCatalogueQuery(await searchParams)} basePath="/org/courses" />;
}
