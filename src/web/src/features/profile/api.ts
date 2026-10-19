import { call, getApi } from "@/lib/api";

export async function fetchMyProfile() {
  const api = await getApi();
  return call(api.GET("/api/v1/profile/me"));
}
