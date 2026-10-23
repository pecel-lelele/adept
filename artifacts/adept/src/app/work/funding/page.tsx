import { redirect } from "@/lib/next-compat/router";

/** Members no longer manage learning funds: the organisation pays for training directly. */
export default function Page() {
  redirect("/work/plan");
}
