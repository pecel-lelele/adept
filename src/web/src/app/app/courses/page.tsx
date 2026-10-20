import { CatalogueView, parseCatalogueQuery } from "@/features/pathway";
import type { SearchParams } from "@/lib/scenario";

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  return <CatalogueView query={parseCatalogueQuery(await searchParams)} basePath="/app/courses" />;
}
