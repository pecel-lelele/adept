# UX flows, navigation and dashboards by audience

Status: proposal by M3 (2026-10-20). It covers flow, routing and navigation, not visual design.
The M3 pages listed here exist; the navigation changes for app shells, landing and org setup are
**proposals for M4** (Core / F7 owner) and are not implemented. See `docs/decisions.md` M3-024.

---

## 1. Principles

1. **One question per screen.** Every page answers one thing: "what is changing?" (radar),
   "where could I go?" (matches), "how do I get there?" (pathway), "how far am I?" (progress).
2. **The stepper is the spine.** Steps 1–4 from the handbook stay the same for every audience.
   Only the words and one or two screens change (config, not separate apps; PROJECT_CONTEXT §11.1).
3. **Always a next action.** Every page ends with one primary button to the next step, plus at
   most two secondary links. No dead ends.
4. **The human decides.** The user picks the target role; HR assigns but members can adjust;
   reviewers confirm completions. The app never decides for them.
5. **Same plan for the same facts.** Segment and organisation type change wording and guidance,
   never the ranking or the plan (tested: `tests/api/pathway/test_fairness.py`).
6. **Source, date, estimate** on every recommendation (`MetaBar`), on every screen.

## 2. Two entry points, five audiences

```
/  ── Individual ──> /app/onboarding  ─ segment: working | graduate | switcher
   └─ Organisation ─> /org/setup      ─ type: company (HR / L&D) | institution (career centre / TVET)
```

| Audience | Entry | What they walk away with |
|---|---|---|
| Working adult at risk (Aisyah) | Individual → working | A target role, a plan their employer can fund, proof HR accepts |
| Fresh graduate (Wei Jie) | Individual → graduate | A first role to aim at, a free-first plan, certificates to show |
| Career switcher (Ravi) | Individual → switcher | Roles that reuse their skills, a plan that covers only the gap |
| HR / L&D manager | Organisation → company | Team gap heatmap, an assigned group plan, verified completions for HRD Corp |
| Career centre / TVET advisor | Organisation → institution | Cohort gaps, advisor notes, verified completions per student |

## 3. Individual flows

### 3.1 Shared spine

```
onboarding ─> profile (step 1) ─> radar (step 2) ─> matches (step 3) ─> pathway (step 4) ─> progress
   segment       CV / form          rising,          ranked roles,       ordered courses,      tick, add
                 confirm skills     declining        score parts, gap    weeks, cost, SDG      proof, badges
```

Secondary pages, reachable from the step that needs them, not from the main bar:
`/app/matches/[roleId]` (role detail), `/app/sdg` (from pathway), `/app/courses` (from pathway
and progress), `/app/progress` (from pathway, and as a "Continue" card once a plan is saved).

Returning user: land on **progress** if a plan is saved, otherwise on the first unfinished step.
If new trend data changed the plan, the pathway shows the re-plan banner first (M3, implemented).

### 3.2 What changes per segment

| Screen | Working adult | Fresh graduate | Career switcher |
|---|---|---|---|
| Profile (F1) | Current job title and tasks; HRD Corp eligible? | Course of study, projects, internships | Current job and the tasks they enjoy |
| Radar (F2) | Highlight their current role's risk | Highlight entry-level rising roles | Highlight roles near their current skills |
| Matches (F4) | "Current-role risk" panel | "Where people with your diploma start" | "Skills that carry over" per role |
| Pathway (F5) | **Implemented:** "Before you enrol" → share with HR, HRD Corp filter | **Implemented:** "Start free, keep the proof" → free filter | **Implemented:** "Build on what you have" → compare roles |
| Progress (F5) | Proof goes to HR (`/org/verify`) | Proof to show employers and the career centre | Proof for job applications |

Funding hints follow the facts we hold: HRD Corp-claimable steps are claimed by the employer
(FMM: "Application must be submitted by employers before training date commencement"), so the
working-adult guidance sends them to HR first. Graduates and switchers are rarely
levy-registered employees, so their guidance starts from free courses.

### 3.3 Proposed individual navigation (M4)

- Top bar: the 4-step stepper with the current step highlighted; tick marks on finished steps.
- Right of the bar: scenario toggle (moderate | fast), language, account.
- Mobile: stepper collapses to "Step 3 of 4 · Matches" with a drop-down; the next-step button is
  sticky at the bottom.
- A "My plan" shortcut appears once a plan is saved (→ `/app/progress`).

## 4. Organisation flows

### 4.1 HR / L&D (company)

```
setup ─> members (invite, intake status) ─> radar (industry) ─> gaps (heatmap) ─> plan (group)
                                                                                   │
                                     verify (completions) <── members tick + proof ┘
                                     courses (corporate, HRD Corp-claimable)
                                     sdg (company contribution)
```

The HR dashboard (`/org`) should answer, top to bottom:
1. **Readiness**: members who finished intake, how many have a plan (from `/org/members`).
2. **Biggest gaps**: top 3 skills from the heatmap, each linking to `/org/gaps`.
3. **Waiting for you**: completions to review (`GET /pathway/verifications` → `pending`),
   linking to `/org/verify`. Implemented as a page; the dashboard tile is a proposal.
4. **Funding**: HRD Corp-claimable share of the group plan (`hrd_claimable` on each course).
5. **SDG contribution** (link to `/org/sdg`).

### 4.2 Career centre / TVET (institution)

Same routes; labels and two features change (`organization.type = institution`):

| Company wording | Institution wording | Extra |
|---|---|---|
| Team, members | Cohort, students | Advisor notes per student (F7) |
| Group plan | Cohort plan | Report export for the programme |
| HRD Corp funding tile | Free / subsidised courses tile | Link to MySPIKE / SKM levels for TVET (proposal) |
| Verify completions | Verify completions | The review note doubles as an advisor note |

TVET advisors already work with SKM levels 1–5 (certificate to advanced diploma) managed through
MySPIKE by the Department of Skills Development; showing the SKM level next to a role is a
good-to-have for F4/F7, not built.

### 4.3 Proposed organisation navigation (M4)

Left rail on desktop, bottom tabs on mobile, in this order:
**Overview · Members · Gaps · Plan · Verify (badge with pending count) · Courses · SDG**.
`Verify` and `Courses` exist (M3); their entries in the rail are for M4 to add.

## 5. Verifying completions (implemented, M3-022)

```
learner ticks "Mark done"            ─> self_reported
learner pastes certificate link      ─> certificate_link (+ provider page check: official page? opens?)
HR / advisor confirms (with a note)  ─> org_confirmed      badge shows the weakest evidence behind it
HR / advisor rejects  (with a note)  ─> org_rejected       completion no longer counts
```

- Official verification pages recognised: Coursera accomplishments/verify, Microsoft Learn
  `/users/` transcripts, Credly badges. Anything else is accepted but marked "needs a manual check".
- Reviewers see only members of their own organisation.
- For HRD Corp-claimable courses the hint tells HR to check the provider's attendance record in
  the HRD Corp claim, which is the record they already have to keep.
- The app never certifies anything itself; it records who confirmed what and when.

## 6. Comparable platforms and business models

What exists, so we position against it rather than rebuild it. Descriptions come from the linked
pages and from public descriptions found while researching; no figures beyond those stated there.

| Platform | Who it serves | What it does | Lesson for us |
|---|---|---|---|
| MyMahir.my (TalentCorp) | Malaysian workers, employers | National skills-intelligence platform linking skills intelligence, training pathways and employment; built on the MyMahir Impact Study of at-risk and emerging roles ([HR Online](https://www.humanresourcesonline.net/malaysia-introduces-new-mymahir-national-ai-council-to-future-proof-the-workforce-with-ai-skills)) | National-level intelligence; we add a personal, explainable plan and SDG link on top |
| MYFutureJobs (PERKESO / KESUMA) | Job seekers, employers | National job portal with career services ([The Star, 2026-07-22](https://www.thestar.com.my/news/nation/2026/07/22/four-in-10-vacancies-on-myfuturejobs-portal-are-high-skilled-says-ramanan)) | Jobs, not reskilling plans; a future integration, out of scope now |
| HRD Corp claimable courses | Levy-paying employers | Employers apply for the grant and claim afterwards ([HRD Corp basic flow](https://supportcentre.hrdcorp.gov.my/portal/en/kb/articles/hrd-corp-claimable-courses-scheme-basic-flow-to-apply-training-and-claim)) | Why the working-adult flow routes through HR |
| MySPIKE (DSD, MOHR) | TVET centres, trainees | Manages training, assessment and SKM certification | TVET advisors think in SKM levels |
| MyTVET.my | TVET learners | Independent course finder: 7,574 courses across 1,140 institutions, states it is not an official site ([mytvet.my](https://mytvet.my)) | A catalogue source to evaluate for TVET courses |
| Handshake | University career centres, students | Career-services platform: jobs, events, advisor appointments ([Capterra](https://www.capterra.com/p/10004289/Handshake/)) | Career centres want appointments and notes, not just dashboards |
| Gloat | Large employers | Internal talent marketplace built on employee skill profiles; managers see team skill gaps ([VentureBeat](https://venturebeat.com/ai/gloat-which-uses-ai-to-connect-employees-with-internal-work-raises-57m)) | HR buys the team view; recommendations are only as good as the data |
| Eightfold | Large employers | AI talent-intelligence platform with skill development and career paths | Same buyer; our angle is SDG and the Malaysian funding context |

**Business models that would scale this** (options, not decisions):

1. **B2B2C via employers (most likely):** HR pays per seat for the organisation view; employees
   use the individual view free. HRD Corp-claimable courses make the plan cheap for the employer.
2. **Institution licence:** career centres and TVET colleges pay per cohort for the advisor view
   and reports; students use it free.
3. **Training-provider listings:** providers pay to be *listed* (never to be ranked higher);
   ranking stays on cost, time and fit. This needs clear labelling to keep trust.
4. **Public-sector partnership:** a free national tier (as MyMahir does) with data shared back
   as aggregated, anonymised skill-gap trends.

Risk to name in the proposal: options 3 and 4 create incentives to bias recommendations; the
catalogue-only rule and the fairness tests are what keep the ranking honest.

## 7. What M3 changed for this (all inside F5/F6/F8)

| Route | Change |
|---|---|
| `/app/pathway` | Segment guidance card; links to courses, progress, SDG |
| `/app/progress` | Saving feedback, evidence badges, certificate links, reviewer notes |
| `/app/courses`, `/org/courses` | Catalogue browse with filters |
| `/org/plan` | Links to verify and to corporate courses |
| `/org/verify` | Review queue for HR / advisors |
