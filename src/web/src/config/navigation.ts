import type { Messages } from "next-intl";

export type NavKey = keyof Messages["ui"]["nav"];
/** Icon names resolved on the client (lucide-react), so config stays serialisable. */
export type IconName =
  | "home" | "skills" | "radar" | "roles" | "plan" | "progress" | "courses" | "impact"
  | "team" | "gaps" | "verify" | "settings" | "sources" | "snapshots" | "jobs";

export type NavItem = {
  key: NavKey;
  href: string;
  icon: IconName;
  /** Journey stage: six for learners, four for organisations. */
  step?: 1 | 2 | 3 | 4 | 5 | 6;
  /** Pages that show the AI-scenario switch. */
  scenario?: boolean;
};

export type NavGroup = { label: NavKey; items: readonly NavItem[] };

export type Workspace = {
  mode: "individual" | "employee" | "organisation" | "admin";
  home: string;
  groups: readonly NavGroup[];
  /** Exactly four destinations for the mobile tab bar; the fifth tab opens "More". */
  tabs: readonly NavKey[];
};

const learnerItems = {
  home: { key: "home", href: "/app", icon: "home" },
  skills: { key: "skills", href: "/app/profile", icon: "skills", step: 1, scenario: true },
  radar: { key: "radar", href: "/app/radar", icon: "radar", step: 2, scenario: true },
  roles: { key: "roles", href: "/app/matches", icon: "roles", step: 3, scenario: true },
  plan: { key: "plan", href: "/app/pathway", icon: "plan", step: 4, scenario: true },
  progress: { key: "progress", href: "/app/progress", icon: "progress", step: 5, scenario: true },
  courses: { key: "courses", href: "/app/courses", icon: "courses" },
  impact: { key: "impact", href: "/app/sdg", icon: "impact", step: 6, scenario: true },
  jobs: { key: "jobs", href: "/app/jobs", icon: "jobs", scenario: true },
} satisfies Record<string, NavItem>;

export const learnerWorkspace: Workspace = {
  mode: "individual",
  home: "/app",
  groups: [
    {
      label: "journey",
      items: [learnerItems.home, learnerItems.skills, learnerItems.radar, learnerItems.roles, learnerItems.plan, learnerItems.progress, learnerItems.impact],
    },
    { label: "track", items: [learnerItems.jobs, learnerItems.courses] },
  ],
  tabs: ["home", "radar", "roles", "plan"],
};

/**
 * An organisation member's workspace (/work): their own participation only. Same familiar
 * destinations as the personal workspace, with the employer's programmes, agreements and funds.
 */
export const workWorkspace: Workspace = {
  mode: "employee",
  home: "/work",
  groups: [
    {
      label: "myWork",
      items: [
        { key: "home", href: "/work", icon: "home" },
        { key: "skills", href: "/work/skills", icon: "skills" },
        { key: "plan", href: "/work/plan", icon: "plan" },
        { key: "progress", href: "/work/progress", icon: "progress", scenario: true },
      ],
    },
  ],
  tabs: ["home", "skills", "plan", "progress"],
};

const orgItems = {
  home: { key: "home", href: "/org", icon: "home" },
  team: { key: "team", href: "/org/members", icon: "team", step: 1 },
  radar: { key: "radar", href: "/org/radar", icon: "radar", step: 2, scenario: true },
  gaps: { key: "gaps", href: "/org/gaps", icon: "gaps", step: 3, scenario: true },
  programmes: { key: "programmes", href: "/org/programmes", icon: "plan", step: 4, scenario: true },
  teamPlan: { key: "teamPlan", href: "/org/plan", icon: "plan", scenario: true },
  impact: { key: "impact", href: "/org/sdg", icon: "impact", scenario: true },
  courses: { key: "courses", href: "/org/courses", icon: "courses" },
  verify: { key: "verify", href: "/org/verify", icon: "verify" },
  settings: { key: "settings", href: "/org/setup", icon: "settings" },
} satisfies Record<string, NavItem>;

export const orgWorkspace: Workspace = {
  mode: "organisation",
  home: "/org",
  groups: [
    {
      label: "journey",
      items: [orgItems.home, orgItems.team, orgItems.radar, orgItems.gaps, orgItems.programmes],
    },
    {
      label: "manage",
      items: [orgItems.teamPlan, orgItems.verify, { key: "funding", href: "/org/funding", icon: "courses" }, orgItems.impact, orgItems.courses, orgItems.settings],
    },
  ],
  tabs: ["home", "team", "gaps", "programmes"],
};

export const adminWorkspace: Workspace = {
  mode: "admin",
  home: "/admin",
  groups: [
    {
      label: "admin",
      items: [
        { key: "sources", href: "/admin/sources", icon: "sources" },
        { key: "snapshots", href: "/admin/snapshots", icon: "snapshots" },
      ],
    },
  ],
  tabs: ["sources", "snapshots"],
};

export function allItems(ws: Workspace): NavItem[] {
  return ws.groups.flatMap((g) => g.items);
}

export function journeyStepCount(ws: Workspace = learnerWorkspace): number {
  return allItems(ws).filter((item) => item.step !== undefined).length;
}

/** The nav item a pathname belongs to (longest matching prefix wins). */
export function activeItem(ws: Workspace, pathname: string): NavItem | undefined {
  return allItems(ws)
    .filter((i) => pathname === i.href || (i.href !== ws.home && pathname.startsWith(i.href + "/")) || pathname === i.href)
    .sort((a, b) => b.href.length - a.href.length)[0];
}
