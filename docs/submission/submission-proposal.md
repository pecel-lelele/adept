# SDC HACKATHON 2026

Phase 2: Final Project & Prototype Report

Hosted by Xiamen University Malaysia (XMUM) AI Club

Submission Deadline: 1 November 2026

## 1. Team & Project Overview

| Field | Response |
|---|---|
| Team Name | Pecel Lele |
| Project / Product Name | Adept |
| Final Live Deployment URL | https://adept-my.replit.app (previously reachable; deployed revision and current snapshot not verified against source `main` at `0a7868c`, 31 October 2026) |
| Codebase Repository URL | https://github.com/pecel-lelele/adept |
| Name (Leader) | David Kurniawan (team record) |
| Email & phone (Leader) | PRIVATE COMPLETION REQUIRED in the organiser submission copy; never commit personal contact details. |

## 2. Project Description [Maximum 250 words]

<!-- answer:start final-2 limit=250 -->
Adept is a human-led, sourced reskilling-planning tool. A learner confirms skills from a form or synthetic demonstration CV, explores dated AI-research signals, compares catalogue-backed roles and gaps, then chooses an ordered course plan within time and budget. Moderate and Fast are assumption-based scenarios, not calibrated employment forecasts. Research attention and a US labour baseline are proxies; Malaysian job listings and national labour statistics are displayed with their own scope and dates, not substituted for a Malaysian role-demand forecast.

Employers or career centres can invite members, view consent-gated aggregate gaps, propose programmes and review progress. Members decide whether to share skills and accept a programme; private plans remain separate. Role/skill links to UN SDG targets are curated explanations, not verified SDG outcomes. Adi, when configured, selects validated server-written answer blocks; default assistance is deterministic. Recommendations carry source, snapshot, scenario and estimate metadata. The application does not hire, fire or certify anybody. The competition demo uses public reference records and synthetic people only. Adept's intended first commercial workflow is an L&D manager choosing which training to fund for a small operations cohort; demand and willingness to pay have not been tested.
<!-- answer:end final-2 -->

## 3. Upgraded Product & Technical Execution

### 3.1 Final System Architecture

Provide a detailed description (and, if possible, an attached technical diagram) of your fully built system. Explain how your application integrates GenAI APIs, database structures, and backend/frontend frameworks into one unified solution.

A single public Next.js 16 server presents learner, employee and manager views and proxies requests to a private FastAPI/Python 3.11 process. Signed accounts, profiles, memberships, catalogue references, snapshots, plans and evidence live in Replit's managed PostgreSQL; server-side membership, manager and consent checks guard organisation data. The local/CI database is PostgreSQL 16 with pgvector. Production startup checks readiness but does **not** migrate or seed.

Daily GitHub Actions supplies a clock and authenticated trigger; the deployed application, not the GitHub runner, fetches and publishes through its own database connection. A shared durable job with an advisory lock checks source cadence, fetches public arXiv submissions, documented job feeds, provider catalogue pages and DOSM context, uses a RunPod-hosted MiniLM encoder for research matching, validates provenance and atomically publishes eligible snapshots. Stored signals can be rescored without another model call. The older manual GitHub trend path is retained as backup. Page views read stored records; missing rows may use **labelled historical fixture fallback**, not pretend a fresh publication. Optional Gemini embeddings support explicit unfamiliar-skill suggestions. The default `auto` trend matcher requires a passing equivalence report before switching to Gemini; an explicit operator override can bypass that gate and must be disclosed. Optional GLM-5.3 with Gemini failover selects validated Adi answer IDs; matching and plans remain deterministic. Neither configured code nor a reachable home page proves a fresh deployed snapshot.

```text
Public sources ──> shared bounded refresh ──> validated dated PostgreSQL snapshot
  arXiv / jobs / courses / DOSM          │           │
                              RunPod MiniLM          │
                                                      ▼
Learner / manager ──> Next.js ──> private FastAPI ──> catalogue + profile
                                                      │
                         explained match → gap → ordered plan → SDG alignment
```

Method: public sources → bounded cleaning → catalogue-ID mapping and paper-mention features → documented heuristic scoring and scenarios → finite/coverage/date validation → dated database snapshots and sourced UI.

### 3.2 Implementation & Hackathon Deliverables [Maximum 300 words]

Describe what was successfully built, integrated, and deployed during the 48-hour physical sprint. Highlight any specific problem-solving steps your team took to pivot or improve the project from the Phase 1 preliminary design.

<!-- answer:start final-3.2 limit=300 -->
The Phase 1 submission described a source-grounded journey and proposed evaluation targets; it was not proof of a commercial service. Since the **25 October 2026, 08:00 MYT cutoff** (`b34c06c`, the last earlier main commit at 07:46), source changes added persisted provenance, bounded daily app-side refresh with recovery and per-source status, clearer empty/stale states, score explanations, consent-gated workspaces and programme/funding improvements. Trend signals feed role scores; the Future Skills Radar page shows signal and role-direction cards, while its trend-line charts are deferred to future work. An unchanged-data check is not a new observation. October 2024 research remains historical. Curated roles/courses are not automatically discovered.

The build uses one public web server and a private API, generated contracts, signed sessions, a managed PostgreSQL database and optional RunPod/Gemini integrations. The original GitHub-hosted trend refresher could not reach Replit's private development database; the new authenticated app-side worker is designed to use its own connection. It still requires migration, configuration, a successful scheduled run and a verified production snapshot before the team can describe it as running automatically on the public deployment. Tests and a local isolated 15-journey synthetic run verify defined source-code paths, not the deployed revision or human outcomes.

The exact official 48-hour sprint start/end and qualifying commit list were not supplied. Do not claim every post-cutoff change happened during the physical sprint; reconcile Git timestamps and deployment history. Complete a live six-must-have change test before signing the checklist.
<!-- answer:end final-3.2 -->

## 4. Environmental & SDG Impact Verification

| Metric Category | Your Response |
|---|---|
| Target SDG Metric Achievement (Direct comparison between your Phase 1 baseline and your Phase 2 finalized prototype numbers) | Phase 1 baseline (actual Phase 1 PDF, page 10): a problem-context figure, Hays Malaysia 2025 survey, 56% of professionals using AI at work and 26% receiving training (verify methodology before quoting); these are not Adept's pre-intervention KPI. Phase 1 prototype targets: 100% catalogue-ID validity and median intake-to-valid-plan below three minutes across five synthetic demo profiles (not a 20% reduction; no manual planning-time baseline was recorded). Phase 2: no independent catalogue-ID audit or human timed study demonstrates either target; the saved calculator has 0/15 matched human cases attempted in each arm and null medians. No percentage improvement or measured SDG outcome is claimed. |
| Verification Evidence Method (How was this data verified?) | An isolated local TestClient run completed 15/15 scripted API journeys on five synthetic profiles, with reported per-persona medians 0.091-0.236 seconds for machine execution; it excluded browser time, human review, network and production data. Source: automated journey record. The human calculator remains unrun. Catalogue-ID checks require a distinct audit of emitted IDs against authoritative catalogue records. |
| Socio-Economic / Civic Value (How does your deployed application translate into a scalable, real-world solution capable of being supported by civic or corporate partners?) | Hypothesis: help Malaysian HR/L&D direct training funds toward explained skill gaps, with members retaining choice. Curated target/role SDG mappings offer a reason to choose a learning path, not proof of job placement or SDG 4 indicator gains. A pilot with a real buyer and independent plan review is needed after separate privacy approvals. |
| Deployment & Commercial Feasibility | Replit-first one-web/one-API plus managed PostgreSQL and shared, not per-view, ingestion. Public reachability was previously observed but source revision and fresh pipeline publication remain unverified. Subscription price, billable worker time, retention, human service hours, legal data rights and procurement cycle are unmeasured; the illustrative calculations in 4.1 are not current profit. |

### 4.1 Mathematical Proof / Code Logic Snippet (Optional, but holds bonus marks)

**What the implemented method can prove:** a role-fit estimate is `fit = 0.45 × skill_overlap + 0.25 × trend_fit + 0.30 × interest_fit` (`src/api/app/features/matching/scoring.py`, `Weights` and `score_role`), where `skill_overlap = Σ importance × min(user_level / required_level, 1) / Σ importance` and a missing interest profile contributes a neutral 0.5. Weights sum to 1, so fit stays in [0, 1]. This is the score before optional SDG weighting: when a learner sets the SDG slider to `w` (0–1), each of the three weights is scaled by `1 − w` and an SDG component is added, giving `fit_sdg = (1 − w) × fit + w × sdg_impact` (`src/api/app/features/matching/sdg_weight.py`, `blend_components`). The pathway algorithm chooses prerequisite-ordered, catalogue-resolved courses; uncovered gaps remain visible when no course qualifies. This is inspectable calculation, **not** a calibrated job forecast or measured social outcome. A five-synthetic-persona evidence run used a historical 2026-10-20 fixture and an earlier catalogue; its outputs are not current live impact results.

**Phase 1 KPI arithmetic (not yet measured):** `ID validity % = 100 × resolved recommended course IDs / all recommended course IDs` (undefined if no IDs are recommended). Time target: median over five *human-completed* synthetic-case journeys from intake start to independently reviewed valid plan; report all attempts and failures. A future paired manual comparison may compute `100 × (manual median − Adept median) / manual median`, but **20% was not a Phase 1 target** and the necessary human observations are absent.

**Commercial feasibility illustration, not impact proof:** hypothesise **RM6 per active seat per month** for a **40-seat, three-month** paid pilot. Revenue if all seats pay throughout = `40 seats × RM6/seat/month × 3 months = RM720`, or **RM240 monthly recognised revenue** (cash collected depends on invoicing). With `v` = monthly delivery cost per customer and `F` = fixed monthly operating cost, contribution = `RM240 − v` and break-even paid customers = `ceil(F / (RM240 − v))` only if `v < RM240`. Neither `v` nor `F` is measured; neither margin nor break-even customer count is presently known. HRD Corp training levies do **not** automatically pay for a software subscription.

## 5. Market Viability & Future Scalability Plan [Maximum 250 words]

<!-- answer:start final-5 limit=250 -->
Adept's initial **hypothesis** is an add-on for Malaysian employer HR/L&D teams planning training for AI-exposed operations staff, not an HR/payroll system or employment predictor. HRD Corp confirms a 1% training levy for covered employers with at least ten Malaysian employees; this proves a training budget exists, **not** that Adept subscriptions are claimable or employers will buy. BrioHR lists training administration at RM3 per month with a RM200 minimum and a talent bundle at RM7; Adept must prove its gap-first planning is worth an additional fee.

An eight-to-twelve-week, 25–50-seat pilot would compare manual course selection with independently checked plans, decision time, relevance, consent and support hours. RM6 per active learner per month is an **unvalidated test price**: 40 paid seats for three months would bill RM720, without automatically covering delivery. Renewal requires buyer-confirmed value. No interview, purchase or revenue is claimed.

The existing system shares catalogue and ingestion work, caches dated snapshots, uses deterministic scoring on reads and can process asynchronous refresh jobs against Replit-managed PostgreSQL. Scale-up requires measured concurrency, database/storage bills, worker seconds, restore drills, licence permissions, privacy agreements and human review capacity. Sponsor credits and unpaid team labour are temporary. Only measured bottlenecks should trigger additional workers or a service split. Employers retain training and personnel decisions. Market evidence (HRD Corp's RM2.62bn 2025 training approvals; 4.2m AI-exposed workers) is cited in the PRD.
<!-- answer:end final-5 -->

## 6. Final Submission Checklist

- [ ] The application is fully compiled, live, and accessible via the deployment link provided in Section 1.
- [x] The GitHub (or equivalent) repository contains a clean, well-documented README with installation instructions.
- [ ] The GitHub (or equivalent) repository shows the history of incremental code updates made throughout the official live hacking window.
- [ ] The final pitch deck has been exported and saved as a flattened PDF file.
- [ ] All fields in this template have been completed and word limits respected.

## 7. IP & Originality Declaration

### 7.1 Pre-Existing / Prior-Owned Work

Does this submission include any code, design, research, or other work that any team member created or owned before the start of this hackathon?

[ ] Yes [ ] No [ ] No change from Phase 1 declaration

If yes, briefly describe what was pre-existing and which team member(s) owned it:

Team-leader record from 25 October: No. Adept's implementation was made for the hackathon; the separate KerjaCerdas project was consulted only for general security ideas, not imported. Leader to confirm each member's prior code, design and research and select privately.

### 7.2 Third-Party Code, Datasets, or Models

Does your project use any third-party code libraries, open-source frameworks, public/private datasets, or pre-trained AI models that your team did not create?

[x] Yes [ ] No [ ] No change from Phase 1 declaration

| Name | Type (code/dataset/model) | License |
|---|---|---|
| Next.js, React, Tailwind, next-intl, Recharts, FastAPI, Pydantic | code | Mainly MIT; check each package's installed notices. |
| PostgreSQL, pgvector, psycopg, PyMuPDF | code | PostgreSQL License; psycopg LGPL-3.0 (binary notices); PyMuPDF AGPL-3.0 or commercial licence — distribution review outstanding. |
| arXiv cs.AI metadata, US BLS baseline, O*NET 31.0, UN SDGs, OpenDOSM LFS, employer job feeds, provider courses | dataset | Separate source/provider terms; O*NET and OpenDOSM CC BY 4.0 with attribution; no blanket licence for job ads. |
| Sentence Transformers all-MiniLM-L6-v2; optional GLM-5.3/Gemini family | model | MiniLM Apache-2.0; hosted model/provider terms for GLM/Gemini to be checked. |
| Synthetic personas, curated skills/roles/course links and SDG alignments | dataset | Team-created parts, underlying provider/taxonomy rights retained; not official UN endorsement. |

### 7.3 Employment-Related IP Conflicts

Is any team member currently bound by an employment, internship, or consulting agreement under which their employer could claim ownership of work they create during this hackathon?

[ ] Yes [ ] No [ ] No change from Phase 1 declaration

If yes, please describe the nature of the agreement and which member it concerns:

No member's employment, internship or consulting terms were reviewed here; each member to confirm privately, and the leader to disclose any agreement in the private organiser copy.

## 8. Declaration

By submitting this report, the team leader confirms that the deployed application and data presented above are the original work of the team, completed within the official SDC 2026 hackathon period.

[Signature]

[Date]
