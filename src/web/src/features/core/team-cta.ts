/** Team-account signup reached by first ending the current (personal/member) session. */
export const TEAM_SIGNUP_AFTER_LOGOUT = `/auth/logout?next=${encodeURIComponent("/auth/signup?mode=organisation&role=team")}`;

export type TeamCtaLabel = "tCta" | "tSignIn" | "tCtaOpen" | "tCtaCreate" | "tCtaJoin";

export type TeamCtaLink = {
  href: string;
  /** Key in `ui.landing`. */
  label: TeamCtaLabel;
  /** POST to the logout handler (with the "you'll be signed out" notice) instead of a link. */
  signOutFirst: boolean;
};

export type TeamCta = { primary: TeamCtaLink; secondary: TeamCtaLink | null };

/**
 * The landing's team calls to action for each session state; every label names its destination.
 * - signed out: set up a team (team signup) / "I manage a team already" (sign in, then /org)
 * - team manager (org_admin): open the team workspace
 * - personal learner or organisation member: create a separate team account (signs out first),
 *   or join their team with a code (/app/join). /app/join is never labelled "set up" or "manage".
 */
export function teamCtaFor(account: { kind: string } | null | undefined): TeamCta {
  if (!account) {
    return {
      primary: { href: "/auth/signup?mode=organisation", label: "tCta", signOutFirst: false },
      secondary: { href: `/auth/login?mode=organisation&next=${encodeURIComponent("/org")}`, label: "tSignIn", signOutFirst: false },
    };
  }
  if (account.kind === "org_admin") {
    return { primary: { href: "/org", label: "tCtaOpen", signOutFirst: false }, secondary: null };
  }
  return {
    primary: { href: TEAM_SIGNUP_AFTER_LOGOUT, label: "tCtaCreate", signOutFirst: true },
    secondary: { href: "/app/join", label: "tCtaJoin", signOutFirst: false },
  };
}
