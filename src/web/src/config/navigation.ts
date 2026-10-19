import type { Messages } from "next-intl";

export type NavKey = keyof Messages["common"]["nav"];

export type NavItem = {
  key: NavKey;
  href: string;
  /** Handbook journey step (1-4), if this page is one. */
  step?: 1 | 2 | 3 | 4;
  feature: string;
};

export const individualNav: readonly NavItem[] = [
  { key: "onboarding", href: "/app/onboarding", feature: "F1" },
  { key: "profile", href: "/app/profile", step: 1, feature: "F1" },
  { key: "radar", href: "/app/radar", step: 2, feature: "F2" },
  { key: "matches", href: "/app/matches", step: 3, feature: "F4" },
  { key: "pathway", href: "/app/pathway", step: 4, feature: "F5" },
  { key: "sdg", href: "/app/sdg", feature: "F6" },
  { key: "progress", href: "/app/progress", feature: "F5" },
];

export const organisationNav: readonly NavItem[] = [
  { key: "setup", href: "/org/setup", feature: "F7" },
  { key: "members", href: "/org/members", step: 1, feature: "F7" },
  { key: "radar", href: "/org/radar", step: 2, feature: "F2" },
  { key: "gaps", href: "/org/gaps", step: 3, feature: "F7" },
  { key: "plan", href: "/org/plan", step: 4, feature: "F7" },
  { key: "sdg", href: "/org/sdg", feature: "F6" },
];

export const adminNav: readonly NavItem[] = [
  { key: "sources", href: "/admin/sources", feature: "F2" },
  { key: "snapshots", href: "/admin/snapshots", feature: "F2" },
];
