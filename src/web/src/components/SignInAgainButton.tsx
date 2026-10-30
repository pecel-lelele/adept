"use client";

import { usePathname, useSearchParams } from "next/navigation";

/**
 * Ends the expired session (POST-only logout) and lands on the sign-in page with a return
 * path to the current page. The logout route validates `next` as a same-origin path.
 */
export function SignInAgainButton({ label }: { label: string }) {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  const here = `${pathname}${search ? `?${search}` : ""}`;
  const login = `/auth/login?next=${encodeURIComponent(here)}`;
  return (
    <form method="post" action={`/auth/logout?next=${encodeURIComponent(login)}`}>
      <button type="submit" className="a-btn is-small">
        {label}
      </button>
    </form>
  );
}
