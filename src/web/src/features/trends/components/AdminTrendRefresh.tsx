import { getAccount } from "@/lib/auth/account";

import { TrendRefreshPanel } from "./TrendRefreshPanel";

/** Operational controls stay hidden and server-authorized for ordinary learners and HR. */
export async function AdminTrendRefresh() {
  const account = await getAccount();
  const allowed = (process.env.ADMIN_USER_IDS ?? "").split(",").map((id) => id.trim());
  if (!account || !allowed.includes(account.id)) return null;
  return <section className="a-card"><TrendRefreshPanel /></section>;
}
