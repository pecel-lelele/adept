"use server";

import type { ApiResult } from "@/lib/api";
import { postDataRefresh, type DataRefreshResult } from "@/lib/data-sources";

export type { DataRefreshResult };

/** Admin only: the API checks the signed session against ADMIN_USER_IDS. */
export async function refreshDataSource(source: string): Promise<ApiResult<DataRefreshResult>> {
  return postDataRefresh(source);
}
