"use server";

import { revalidatePath } from "next/cache";

import { call, getApi } from "@/lib/api";

export type OrgActionState = { error?: string; done?: number };

function text(form: FormData, key: string, max = 120): string {
  const value = form.get(key);
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

export async function updateOrgAction(_: OrgActionState, form: FormData): Promise<OrgActionState> {
  const size = Number.parseInt(text(form, "size", 7), 10);
  const org_id = text(form, "org_id");
  const api = await getApi(org_id ? { workspace: org_id } : undefined);
  const result = await call(
    api.PUT("/api/v1/org/me", {
      params: org_id ? { query: { expected_org: org_id } } : undefined,
      body: {
        type: text(form, "type") === "institution" ? "institution" : "company",
        name: text(form, "name"),
        industry: text(form, "industry"),
        size: Number.isFinite(size) && size >= 0 ? size : 0,
      },
    }),
  );
  if (!result.ok) return { error: result.message };
  revalidatePath("/org", "layout");
  return { done: Date.now() };
}

export async function rotateCodeAction(expectedOrg?: string): Promise<OrgActionState> {
  const api = await getApi(expectedOrg ? { workspace: expectedOrg } : undefined);
  const result = await call(
    api.POST("/api/v1/org/me/join-code", {
      params: expectedOrg ? { query: { expected_org: expectedOrg } } : undefined,
    }),
  );
  if (!result.ok) return { error: result.message };
  revalidatePath("/org", "layout");
  return { done: Date.now() };
}

export async function removeMemberAction(memberId: string, expectedOrg?: string): Promise<OrgActionState> {
  const api = await getApi(expectedOrg ? { workspace: expectedOrg } : undefined);
  const result = await call(
    api.DELETE("/api/v1/org/members/{member_id}", {
      params: {
        path: { member_id: memberId },
        query: expectedOrg ? { expected_org: expectedOrg } : undefined,
      },
    }),
  );
  if (!result.ok) return { error: result.message };
  revalidatePath("/org", "layout");
  return { done: Date.now() };
}
