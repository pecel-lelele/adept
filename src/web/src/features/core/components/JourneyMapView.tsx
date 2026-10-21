import Link from "next/link";
const individual: [string, string, string][] = [
  [
    "/try",
    "Guest CV preview",
    "Synthetic upload → extracted skills → one estimated role",
  ],
  [
    "/auth/login?next=/app",
    "Enter a workspace",
    "Demo persona today; production account auth remains separate",
  ],
  [
    "/app",
    "Learning overview",
    "Saved plan, activity points, badges, next course",
  ],
  ["/app/onboarding", "Choose a starting point", "M2 intake handoff"],
  [
    "/app/profile",
    "Review your profile",
    "M2 questionnaire, CV and skill confirmation APIs",
  ],
  ["/app/radar", "Explore trend signals", "M1 owns radar and scenarios"],
  [
    "/app/matches",
    "Compare future roles",
    "M2 score, canonical skills gap and SDGs",
  ],
  [
    "/app/pathway/compare",
    "Compare learning paths",
    "M3 time, cost, skill coverage and SDGs",
  ],
  [
    "/app/pathway",
    "Choose and save a plan",
    "Explicit target role; no automatic choice",
  ],
  [
    "/app/courses",
    "Find a course",
    "Verified source → external provider opens separately",
  ],
  [
    "/app/progress",
    "Track learning",
    "Self-reported completion → evidence → HR review",
  ],
  [
    "/app/sdg",
    "Explore your contribution",
    "Target-level reasons → back to saved pathway",
  ],
];
const organisation: [string, string, string][] = [
  [
    "/auth/login?mode=organisation&next=/org",
    "Enter organisation workspace",
    "Synthetic company demo today",
  ],
  [
    "/org",
    "People development overview",
    "Members, gaps, plan, courses and evidence",
  ],
  ["/org/setup", "Organisation context", "M4 setup API currently read-only"],
  [
    "/org/members",
    "People and intake",
    "M4 membership writes and invites still needed",
  ],
  ["/org/radar", "Industry skills radar", "M1 trend signals and scenario"],
  [
    "/org/gaps",
    "Team skills heatmap",
    "M4 team data with canonical M3 gap logic",
  ],
  [
    "/org/plan",
    "Group learning plan",
    "M3 courses and prerequisites; assignment writes pending",
  ],
  [
    "/org/courses",
    "Team course library",
    "Provider, delivery, budget and HRD filters",
  ],
  [
    "/org/verify",
    "Review learning evidence",
    "Confirm or reject evidence for own organisation",
  ],
  ["/org/sdg", "Team SDG contribution", "Aggregate member and role mappings"],
];
export function JourneyMapView() {
  return (
    <main className="preview-page">
      <header>
        <Link className="workspace-brand" href="/">
          adept.
        </Link>
        <Link href="/try">Try a synthetic CV ↗</Link>
      </header>
      <span className="workspace-eyebrow">TEAM ROUTE ATLAS</span>
      <h1>Two workspaces. One learning journey.</h1>
      <p>
        Each card opens its route. Arrows show the recommended sequence; the
        workspace sidebar supports direct navigation. Previous/next controls
        retain role, scenario and snapshot date. Browser Back follows actual
        history.
      </p>
      <div className="route-columns">
        {[
          { items: individual, label: "Individual" },
          { items: organisation, label: "Organisation" },
        ].map(({ items, label }) => (
          <section key={label}>
            <h2>{label}</h2>
            {items.map(([href, title, note], index) => (
              <div key={href}>
                {index > 0 ? (
                  <div className="route-arrow" aria-hidden>
                    ↓
                  </div>
                ) : null}
                <Link href={href} className="route-node">
                  {title}
                  <small>
                    {href.split("?")[0]} · {note}
                  </small>
                </Link>
              </div>
            ))}
          </section>
        ))}
      </div>
      <p>
        Cross-feature branches: role detail → pathway or compare; pathway →
        courses, progress or SDGs; new signals → review proposed re-plan →
        explicitly accept. Learning completion never automatically certifies
        proficiency.
      </p>
      <p>
        Guest preview returns only one role. Demo entry does not import
        anonymous skills into an existing persona. The landing page can link to
        /try without a redesign.
      </p>
    </main>
  );
}
