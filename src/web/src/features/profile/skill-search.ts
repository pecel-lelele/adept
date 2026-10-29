/** Pure search helpers: aliases work without a resolver or an embedding provider. */
type SearchOption = { id: string; label: string; aliases?: readonly string[] };

export function normaliseSkillQuery(query: string): string {
  return query.normalize("NFKC").toLowerCase().trim().replace(/\s+/g, " ");
}

export function filterCatalogueSkills<T extends SearchOption>(
  catalogue: readonly T[], query: string, chosen: ReadonlySet<string>,
): T[] {
  const key = normaliseSkillQuery(query);
  if (!key) return [];
  return catalogue.filter((option) => !chosen.has(option.id) &&
    [option.id, option.label, ...(option.aliases ?? [])]
      .some((text) => normaliseSkillQuery(text).includes(key))).slice(0, 12);
}

export function canResolveSkill(query: string): boolean {
  const key = normaliseSkillQuery(query);
  return key.length <= 80 && (key.match(/[\p{L}\p{N}]/gu)?.length ?? 0) >= 4;
}

/** One wizard session, memory only. Cache pending calls and successful empty results too. */
export function createSessionResolver<T extends { ok: boolean }>(load: (query: string) => Promise<T>) {
  const cache = new Map<string, Promise<T>>();
  return (query: string): Promise<T> | null => {
    const key = normaliseSkillQuery(query);
    if (!canResolveSkill(key)) return null;
    const cached = cache.get(key);
    if (cached) return cached;
    const pending = load(key).then((result) => {
      if (!result.ok) cache.delete(key);
      return result;
    }).catch((error: unknown) => {
      cache.delete(key);
      throw error;
    });
    if (cache.size >= 128) cache.delete(cache.keys().next().value!);
    cache.set(key, pending);
    return pending;
  };
}
