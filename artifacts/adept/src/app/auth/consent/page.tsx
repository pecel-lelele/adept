import { redirect } from "@/lib/next-compat/router";

/** Consent is part of sign-up now; keep the old link working. */
export default function Page() {
  redirect("/auth/signup");
}
