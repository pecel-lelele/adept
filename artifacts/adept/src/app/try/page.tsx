import { redirect } from "@/lib/next-compat/router";

/** The CV preview now lives on the home page. */
export default function Page() {
  redirect("/#start");
}
