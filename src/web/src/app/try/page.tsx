import { redirect } from "next/navigation";

/** The CV preview now lives on the home page. */
export default function Page() {
  redirect("/#start");
}
