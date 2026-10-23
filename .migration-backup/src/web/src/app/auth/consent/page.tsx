import { redirect } from "next/navigation";

/** Consent is part of sign-up now; keep the old link working. */
export default function Page() {
  redirect("/auth/signup");
}
