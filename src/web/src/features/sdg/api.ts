import { call, getApi } from "@/lib/api";

export async function fetchMyContribution() {
  const api = await getApi();
  return call(api.GET("/api/v1/sdg/contribution/me"));
}

export async function fetchRoleSdg(roleId: string) {
  const api = await getApi();
  return call(api.GET("/api/v1/sdg/roles/{role_id}", { params: { path: { role_id: roleId } } }));
}
