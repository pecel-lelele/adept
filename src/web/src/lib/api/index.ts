import type { components } from "./types";

export { API_URL, call, createApiClient, type ApiClient, type ApiResult } from "./client";
export { getApi } from "./server";

/** Generated contract types: `make contracts` regenerates ./types.ts. */
export type Schemas = components["schemas"];
export type Source = Schemas["Source"];
export type RecommendationMeta = Schemas["RecommendationMeta"];
export type ScenarioId = RecommendationMeta["scenario"];
