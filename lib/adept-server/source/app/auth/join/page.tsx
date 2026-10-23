import { redirect } from "next/navigation";

import { getAccount } from "@/lib/auth/account";
import { firstParam, type SearchParams } from "@/lib/scenario";

/** Join links (/auth/join?code=XXXX): new people sign up with the code, members join in-app. */
export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const code = firstParam((await searchParams).code) ?? "";
  const account = await getAccount();
  const query = code ? `?code=${encodeURIComponent(code)}` : "";
  if (!account) redirect(`/auth/signup${query}`);
  if (account.kind === "org_admin") redirect("/org");
  redirect(`/app/join${query}`);
}
