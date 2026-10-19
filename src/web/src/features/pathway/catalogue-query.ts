import { firstParam, type SearchParams } from "@/lib/scenario";

import type { CatalogueQuery } from "./components/CatalogueView";

const FORMATS = ["self_paced", "live_online", "in_person", "hybrid", "subscription"] as const;
const PROVIDERS = [
  "mooc",
  "university",
  "industry_body",
  "professional_body",
  "private_provider",
  "government",
] as const;
const AUDIENCES = ["individual", "corporate"] as const;

function pick<T extends string>(allowed: readonly T[], raw: string | undefined): T | undefined {
  return allowed.find((v) => v === raw);
}

/** Only known values reach the API; anything else is ignored rather than erroring. */
export function parseCatalogueQuery(params: SearchParams): CatalogueQuery {
  const cost = Number.parseFloat(firstParam(params.max_cost_myr) ?? "");
  const skill = firstParam(params.skill)?.slice(0, 60);
  return {
    skill: skill || undefined,
    format: pick(FORMATS, firstParam(params.format)),
    provider_type: pick(PROVIDERS, firstParam(params.provider_type)),
    audience: pick(AUDIENCES, firstParam(params.audience)),
    hrd_claimable: firstParam(params.hrd_claimable) === "true" ? true : undefined,
    max_cost_myr: Number.isFinite(cost) && cost >= 0 ? cost : undefined,
  };
}
