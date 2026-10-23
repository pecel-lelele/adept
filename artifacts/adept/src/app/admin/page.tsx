import { redirect } from "@/lib/next-compat/router";

export default function Page() {
  redirect("/admin/sources");
}
