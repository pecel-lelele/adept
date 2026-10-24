# Solution Design: the skills-signal engine

This document explains **what problem Adept solves, how the system works end to end, and how
each of the four target users moves through it**. It is the design reference for the
proposal's "approach" section. Feature-level choices live in `docs/decisions.md`.

---

## 1. Core problem: the skills-signal gap

In Malaysia, workers, employers and training institutions make reskilling decisions
**without a current, trustworthy signal of how AI is changing skill demand**.

| Who | What goes wrong today | Cost |
|---|---|---|
| Workers | Pick generic courses from static lists; can't tell which skills AI will augment vs replace | Limited hours wasted; displacement risk unaddressed |
| Employers (HR / L&D) | Spend HRD Corp levy and training budgets on guesses, not on the team's real gap | Levy spent, roles still unfilled |
| Institutions (TVET / universities) | Teach to frameworks that lag AI by years | Graduates trained for yesterday's jobs |
| Society | Growing roles, including those that advance the SDGs, go unfilled | Missed SDG 4 / 8 progress |

Domain evidence (cited in the handbook): 56% of Malaysian professionals use AI at work but only
26% have had formal training (Hays Asia Salary Guide 2025); MOSTI says 600,000+ workers need
reskilling within three to five years.

## 2. Core solution: a continuously updated skills-signal engine

```
 dated public data            engine                                   people
 ─────────────────   ─────────────────────────────────────────   ─────────────────────
 AI / job-market  ─► F2 snapshots ─► F3 outlook (moderate|fast) ─┐
 trend sources                                                   ├► F4 match + gap ─► F5 pathway ─► person / team
 profile (F1)  ──────────────────────────────────────────────────┘          │              │
 UN SDG API  ───► F6 SDG targets + reviewed role/skill links ────────────────┴──────────────┴► F6 contribution
 course catalogue (Microsoft Learn API + verified providers) ─► F5 catalogue
                         F8 guardrails wrap every step (sources, IDs, PII, fairness)
```

1. **Ingest** dated, versioned public data (trend snapshots, the official UN SDG list, a course
   catalogue pulled from a public API plus manually verified provider pages).
2. **Forecast** role and skill demand under two AI-disruption scenarios with low/high ranges.
3. **Match** people to future roles with an explainable score (parts shown) and a skills gap.
4. **Plan** an ordered, time-bound, low-cost pathway from catalogue courses only, sized to the
   learner's hours per week and budget (HRD Corp claimability lowers out-of-pocket cost).
5. **Connect** every role, skill and pathway to specific SDG targets with a reason and a
   direct/enabling strength; aggregate for a person, an organisation or a region.
6. **Re-plan** automatically when a new trend snapshot changes the plan, and *propose* the new
   plan; the human accepts or keeps the old one.

Every recommendation carries `meta = {sources[], snapshot_date, scenario, is_estimate}`.
Humans make the final decision: the user picks the target role, saves the plan, and accepts
re-plans. Adept never makes hiring decisions.

## 3. How it works for each of the four users

### 3.1 Working adult at risk of displacement (persona: Aisyah, 34, bank operations)

| Step | Route | What she sees | Engine |
|---|---|---|---|
| Start | `/` CV upload → partial result → `/auth/signup` → `/app/onboarding` (skills from the CV carried over) | Segment = *working* | F1 |
| 1 | `/app/profile` | Confirms extracted skills and levels; sets 6 h/week, RM 500, HRD Corp eligible | F1 |
| 2 | `/app/radar` | Her current role is *declining* (high automation share); adjacent skills are *rising* | F2/F3 |
| 3 | `/app/matches` | Ranked roles with score parts; chooses *Process Automation Analyst* | F4 |
| 4 | `/app/pathway?role=…` | Ordered steps, courses with real URLs, weeks at 6 h/week, out-of-pocket cost vs budget, HRD Corp note, SDG contribution; **saves the plan** | F5/F6 |
| Ongoing | `/app/progress?role=…` | Ticks courses done; earns skill badges; sees gap closing | F5 |
| Re-plan | banner on `/app/pathway` | "New trend data (source, date) changes your plan: …" → accept or keep | F5 + F2 |

Specific to *working*: radar highlights current-role risk; HRD Corp-claimable courses cost her
RM 0 out of pocket (employer applies for the grant), which the plan states explicitly.

### 3.2 Fresh graduate / career switcher (personas: Wei Jie, 22; Ravi, 41)

Same `/app/*` journey with `learner.segment = graduate | switcher`:

- **Graduate**: no current role, so matching leans on interests and existing partial skills;
  pathway favours free courses (budget RM 200) and more hours per week (15) → shorter plan.
- **Switcher**: radar shows *transferable* skills (e.g. logistics planning → process mapping);
  the pathway skips skills he already has at the required level and only schedules the gap.

### 3.3 HR / L&D manager (persona: Demo Bank HR)

| Step | Route | What they see | Engine |
|---|---|---|---|
| Start | `/auth/signup` (For my team) → `/org` → share the join code | Company, industry, size | F7 |
| 1 | `/org/members` | Who has completed intake | F7 |
| 2 | `/org/radar` | Radar for the banking industry | F2 |
| 3 | `/org/gaps` | Heatmap: share of members missing each skill for each target role | F7 (+ F5 gap function) |
| 4 | `/org/plan?scenario=…` | One group pathway for a target role; each step lists the members who need it; HRD Corp levy note | F5 group plan |
| SDG | `/org/sdg` | Aggregated SDG contribution of the team's plan; region view | F6 |

### 3.4 TVET / university career centre (persona: Demo Polytechnic)

Same `/org/*` routes with `organization.type = institution`: labels say *cohort* instead of
*team*, plans are advisory (students adjust), and the SDG view emphasises 4.3 (equal access to
affordable TVET) and 4.4 (relevant skills for decent work).

## 4. M3 features in detail

### F5 Reskilling pathway

How the core problem shows up: pathways are static, generic course lists that go stale and
ignore time, budget and existing skills.

Engine (pure, testable functions in `src/api/app/features/pathway/`):

1. **Gap**: role requirements (`role_skills`) minus the learner's confirmed levels → per skill
   `current`, `required`, `status` (have / partial / missing).
2. **Priority**: `importance × gap_share × trend_multiplier(scenario)`; rising skills get a
   larger boost under the *fast* scenario.
3. **Order**: topological sort over a skill prerequisite graph (`skill_prerequisites`), ties
   broken by priority. Cycles are rejected.
4. **Courses**: catalogue courses only. For each skill, pick courses in ascending level until
   the required level is reached; prefer HRD Corp-claimable (if eligible) or free, then fewer
   hours; respect the remaining out-of-pocket budget. A course that covers several gap skills is
   scheduled once. A skill with no catalogue course is shown as an unmet gap, never filled with
   an invented course.
5. **Schedule**: cumulative hours ÷ hours per week → contiguous week ranges and total weeks.
6. **Re-plan**: each saved plan records the trend snapshot version it was built on. When a newer
   snapshot exists, the plan is rebuilt and diffed (added / removed / reordered steps) and the
   change is *proposed*.
7. **Progress & badges**: completed courses raise the learner's level for the skills they teach
   (self-reported evidence, labelled as such); a skill badge is earned when the target level is
   reached; milestone badges at first step, halfway and complete.

### F6 SDG mapping

How the core problem shows up: the social impact of a career choice is invisible.

- All **17 goals and 169 targets** come from the UN Statistics Division SDG API (dated snapshot,
  `src/pipelines/sdg`). The domain focus goals are 4, 5, 8, 9 and 10; mappings may use any goal.
- Each role and skill links to ≥1 **target** with a one-line reason, a strength (*direct*:
  the work itself advances the target; *enabling*: it builds capacity that the target needs),
  a reviewer and a review date.
- Pathway-level links are computed from the plan itself (e.g. a plan of free / HRD Corp-funded
  courses contributes to 4.3 equal access to affordable technical education).
- Contribution views aggregate links for a **person** (chosen role + skills the pathway builds),
  an **organisation** (members' plans) and a **region** (organisations in a state).
- `alignment(role, goals)` gives F4 an SDG score for the SDG-weighted ranking slider, so SDG links
  can affect ranking rather than decorate it.

### F8 Guardrails & transparency

How the core problem shows up: AI tools that recommend careers can invent jobs, courses or
statistics; and an open demo API is easy to abuse.

- **Catalogue-only**: the LLM gateway lets a model only *select* IDs from a supplied catalogue;
  `validate_ids` rejects unknown IDs; prompts are PII-redacted and injection-filtered first; a
  circuit breaker fails fast; every call is logged with provider and model.
- **Sources on every recommendation**: a CI test sweeps every endpoint and fails if a
  recommendation response lacks `meta.sources` with a date.
- **LLM disclosure**: `/api/v1/guardrails/disclosure` reports the configured provider and model;
  the About page and README read from it, so the disclosure cannot drift from the config.
- **Fairness**: no contract accepts age, gender, ethnicity, religion or similar (a CI test scans
  every input model); counterfactual tests check that identical skills, hours and budget give
  identical pathways regardless of identity.
- **API security**: per-IP sliding-window rate limiting, request-size limits, capped upload reads,
  security headers, JWT verification for the Supabase auth mode, Postgres bound to localhost.

## 5. Security design references and provenance

KerjaCerdas, a project by a different team, was a conceptual reference for security and
evidence-handling patterns. The Adept team leader clarified on 25 October 2026 that these
concepts were implemented for Adept's own APIs, connections and use cases, rather than
importing a prior implementation. The earlier wording describing the same team and reused
code was inaccurate. This records the team's provenance clarification, not an independent
source-code comparison. Historical decisions remain intact; M3-028 records the correction.

| Concept considered | Adept implementation | Application |
|---|---|---|
| Sliding-window limits and bounded counters | `core/security/rate_limit.py` | Per-IP/route buckets, capped state and trusted-proxy checks |
| Input filtering and request-size limits | `core/security/sanitize.py`, `body_limit.py` | CV uploads, JSON bodies and LLM-bound text |
| Contact-data redaction | `core/security/pii.py` | Malaysian identity/phone formats and CV date-range preservation |
| Fail-closed JWT verification | `core/security/tokens.py` | Optional Supabase HS256 verification and trusted privilege fields |
| Circuit breaker and structured selection | `core/llm/gateway.py` | Provider failures and validated candidate IDs |
| Response security headers | `core/security/headers.py` | API response headers |
| Distinguishable evidence levels | Pathway progress and verification | Self-reported completion remains distinct from reviewed evidence |
| Catalogue grounding | Pathway engine and ID validator | Unknown entities are rejected; uncovered gaps are reported |
| Automated quality gates | `.github/workflows/ci.yml` | Lint, tests, types, contracts and PostgreSQL checks |

Third-party frameworks, datasets, models and actual development tools are declared separately
in the technical declaration. Conceptual inspiration does not imply shared team membership
or establish code ownership.

## 6. Routing summary

```
/  (Individual | Teams)  CV upload ─► partial result ─► /auth/signup ─┐      /auth/login ─┐
                                                                     ▼                   ▼
learner:  /app/onboarding ─► /app (home) ─► /app/radar ─► /app/matches ─► /app/matches/[roleId]
                                 │                              └─► /app/pathway?role= (save plan)
                                 │                                        ├─► /app/progress
                                 │                                        └─► /app/sdg
                                 └─ /app/profile (skills, organisation) ─► /app/join?code=
team:     /auth/signup (For my team) ─► /org ─► /org/members (join code) ─► /org/gaps ─► /org/plan
                                          └─► /org/radar, /org/sdg, /org/courses, /org/verify, /org/setup
/about    LLM disclosure, methodology, sources (with dates), guardrails, fairness
```

API chain behind the pages: `POST /auth/signup|login` → `POST /profile/questionnaire` +
`PUT /profile/skills/confirm` → `GET /trends/snapshot` → `GET /matches` (needs a profile:
`profile_required`) → `GET /pathway?role_id=` → `POST /pathway/plans` → `GET /pathway` and
`/pathway/progress` default to the saved role (`role_required` until one is saved) →
`GET /sdg/contribution/me`. Teams: `POST /org/join` → `GET /org/members|gaps|plan`.

`?scenario=` and `?role=` are preserved by the journey stepper so every page describes the same
plan under the same scenario.

## 7. Hardest risks and fallbacks (M3)

| Risk | Fallback |
|---|---|
| A course URL, price or HRD Corp status changes | Every course carries `verified_at` and its source; the Microsoft Learn part is re-fetched by a pipeline; stale rows are flagged |
| An LLM invents a course or SDG target | The model only selects IDs; unknown IDs raise; the deterministic engine works with no LLM at all (current default) |
| SDG links become decorative | Links need a reason, strength and reviewer; pathway links are computed from plan facts; alignment feeds ranking |
| Trend source goes down | Plans keep the snapshot they were built on; re-planning only proposes changes when a newer snapshot exists |
