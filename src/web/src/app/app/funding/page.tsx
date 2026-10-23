import { redirect } from "next/navigation";

/** Members no longer manage learning funds: the organisation pays for training directly. */
export default function Page() {
  redirect("/work/plan");
}
