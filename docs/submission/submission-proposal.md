# SDC Hackathon 2026 — Phase 2 Final Project & Prototype Report

**Team Pecel Lele · Adept · unsigned public draft · 31 October 2026.** This draft follows the organiser's eight-section finalist template. It describes source on `main` at `0a7868c` (31 October 2026), not an identified Replit release. The competition deadline is 1 November 2026. Export as `SDC2026_Pecel-Lele_Final.pdf`; the leader must complete private fields and declarations in the submission copy. Do not submit this draft as a signed or measured-impact report.

## 1. Team & Project Overview

| Organiser field | Response |
|---|---|
| Team Name | Pecel Lele (confirm registered spelling). |
| Project / Product Name | Adept. |
| Final Live Deployment URL | https://adept-my.replit.app — URL previously reachable; revision, schema and current snapshot not verified against this source. |
| Codebase Repository URL | https://github.com/pecel-lelele/adept — confirm judge access and final commit. |
| Name (Leader) | David Kurniawan (team record; confirm registered details privately). |
| Email & phone (Leader) | **PRIVATE COMPLETION REQUIRED** in the organiser submission copy; never commit personal contact details. |

## 2. Project Description

<!-- answer:start final-2 limit=250 -->
Adept is a human-led, sourced reskilling-planning tool. A learner confirms skills from a form or synthetic demonstration CV, explores dated AI-research signals, compares catalogue-backed roles and gaps, then chooses an ordered course plan within time and budget. Moderate and Fast are assumption-based scenarios, not calibrated employment forecasts. Research attention and a US labour baseline are proxies; Malaysian job listings and national labour statistics are displayed with their own scope and dates, not substituted for a Malaysian role-demand forecast.

Employers or career centres can invite members, view consent-gated aggregate gaps, propose programmes and review progress. Members decide whether to share skills and accept a programme; private plans remain separate. Role/skill links to UN SDG targets are curated explanations, not verified SDG outcomes. Adi, when configured, selects validated server-written answer blocks; default assistance is deterministic. Recommendations carry source, snapshot, scenario and estimate metadata. The application does not hire, fire or certify anybody. The competition demo uses public reference records and synthetic people only. Adept's intended first commercial workflow is an L&D manager choosing which training to fund for a small operations cohort; demand and willingness to pay have not been tested.
<!-- answer:end final-2 -->

## 3. Upgraded Product & Technical Execution

### 3.1 Final System Architecture

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

### 3.2 Implementation & Hackathon Deliverables

<!-- answer:start final-3.2 limit=300 -->
The Phase 1 submission described a source-grounded journey and proposed evaluation targets; it was not proof of a commercial service. Since the **25 October 2026, 08:00 MYT cutoff** (`b34c06c`, the last earlier main commit at 07:46), source changes added persisted provenance, bounded daily app-side refresh with recovery and per-source status, clearer empty/stale states, score explanations, consent-gated workspaces and programme/funding improvements. Trend signals feed role scores; the Future Skills Radar page shows signal and role-direction cards, while its trend-line charts are deferred to future work. An unchanged-data check is not a new observation. October 2024 research remains historical. Curated roles/courses are not automatically discovered.

The build uses one public web server and a private API, generated contracts, signed sessions, a managed PostgreSQL database and optional RunPod/Gemini integrations. The original GitHub-hosted trend refresher could not reach Replit's private development database; the new authenticated app-side worker is designed to use its own connection. It still requires migration, configuration, a successful scheduled run and a verified production snapshot before the team can describe it as running automatically on the public deployment. Tests and a local isolated 15-journey synthetic run verify defined source-code paths, not the deployed revision or human outcomes.

The exact official 48-hour sprint start/end and qualifying commit list were not supplied. Do not claim every post-cutoff change happened during the physical sprint; reconcile Git timestamps and deployment history. Complete a live six-must-have change test before signing the checklist.
<!-- answer:end final-3.2 -->

## 4. Environmental & SDG Impact Verification

The **actual Phase 1 PDF, page 10**, supplies a historical *problem-context baseline*: Hays Malaysia reported 56% of professionals using AI at work and 26% receiving training (2025 survey; verify original methodology before quoting publicly). Its proposed prototype targets were **100% catalogue-ID validity** and **median intake-to-valid-plan below three minutes across five synthetic demo profiles**, not a 20% reduction against manual planning. No Phase 1 measured manual planning-time baseline was recorded. These are separate populations and measures: the Hays percentages are not Adept's pre-intervention KPI.

| Organiser metric category | Verifiable response as of 31 October 2026 |
|---|---|
| Target SDG Metric Achievement / Phase 1 vs Phase 2 | Phase 1: 100% resolved course IDs and <3 minutes median synthetic-persona valid plan **targets**; baseline valid-ID denominator and human-time baseline **not measured**. Phase 2: no independent catalogue-ID audit or human timed study demonstrating either target. The saved calculator has **0/15 matched human cases attempted** in each arm and null medians. No percentage improvement or measured SDG outcome is claimed. |
| Verification Evidence Method | An isolated local TestClient run completed **15/15 scripted API journeys** on five synthetic profiles, with reported per-persona medians **0.091–0.236 seconds** for machine execution; it excluded browser time, human review, network and production data. Source: automated journey record. Human calculator remains unrun. Catalogue-ID checks require a distinct audit of emitted IDs against authoritative catalogue records. |
| Socio-Economic / Civic Value | Hypothesis: help Malaysian HR/L&D direct training funds toward explained skill gaps, with members retaining choice. Curated target/role SDG mappings offer a reason to choose a learning path, not proof of job placement or SDG 4 indicator gains. Pilot with a real buyer and independent plan review is needed after separate privacy approvals. |
| Deployment & Commercial Feasibility | Replit-first one-web/one-API plus managed PostgreSQL and shared, not per-view, ingestion. Public reachability was previously observed but source revision and fresh pipeline publication remain unverified. Subscription price, billable worker time, retention, human service hours, legal data rights and procurement cycle are unmeasured; symbolic and illustrative calculations below are **not current profit**. |

### 4.1 Mathematical Proof / Code Logic Snippet (optional)

**What the implemented method can prove:** a role-fit estimate is `fit = 0.45 × skill_overlap + 0.25 × trend_fit + 0.30 × interest_fit` (`src/api/app/features/matching/scoring.py`, `Weights` and `score_role`), where `skill_overlap = Σ importance × min(user_level / required_level, 1) / Σ importance` and a missing interest profile contributes a neutral 0.5. Weights sum to 1, so fit stays in [0, 1]. The pathway algorithm chooses prerequisite-ordered, catalogue-resolved courses; uncovered gaps remain visible when no course qualifies. This is inspectable calculation, **not** a calibrated job forecast or measured social outcome. A five-synthetic-persona evidence run used a historical 2026-10-20 fixture and an earlier catalogue; its outputs are not current live impact results.

**Phase 1 KPI arithmetic (not yet measured):** `ID validity % = 100 × resolved recommended course IDs / all recommended course IDs` (undefined if no IDs are recommended). Time target: median over five *human-completed* synthetic-case journeys from intake start to independently reviewed valid plan; report all attempts and failures. A future paired manual comparison may compute `100 × (manual median − Adept median) / manual median`, but **20% was not a Phase 1 target** and the necessary human observations are absent.

**Commercial feasibility illustration, not impact proof:** hypothesise **RM6 per active seat per month** for a **40-seat, three-month** paid pilot. Revenue if all seats pay throughout = `40 seats × RM6/seat/month × 3 months = RM720`, or **RM240 monthly recognised revenue** (cash collected depends on invoicing). With `v` = monthly delivery cost per customer and `F` = fixed monthly operating cost, contribution = `RM240 − v` and break-even paid customers = `ceil(F / (RM240 − v))` only if `v < RM240`. Neither `v` nor `F` is measured; neither margin nor break-even customer count is presently known. HRD Corp training levies do **not** automatically pay for a software subscription.

## 5. Market Viability & Future Scalability Plan

<!-- answer:start final-5 limit=250 -->
Adept's initial **hypothesis** is an add-on for Malaysian employer HR/L&D teams planning training for AI-exposed operations staff, not an HR/payroll system or employment predictor. HRD Corp confirms a 1% training levy for covered employers with at least ten Malaysian employees; this proves a training budget exists, **not** that Adept subscriptions are claimable or employers will buy. BrioHR lists training administration at RM3 per month with a RM200 minimum and a talent bundle at RM7; Adept must prove its gap-first planning is worth an additional fee.

An eight-to-twelve-week, 25–50-seat pilot would compare manual course selection with independently checked plans, decision time, relevance, consent and support hours. RM6 per active learner per month is an **unvalidated test price**: 40 paid seats for three months would bill RM720, without automatically covering delivery. Renewal requires buyer-confirmed value. No interview, purchase or revenue is claimed.

The existing system shares catalogue and ingestion work, caches dated snapshots, uses deterministic scoring on reads and can process asynchronous refresh jobs against Replit-managed PostgreSQL. Scale-up requires measured concurrency, database/storage bills, worker seconds, restore drills, licence permissions, privacy agreements and human review capacity. Sponsor credits and unpaid team labour are temporary. Only measured bottlenecks should trigger additional workers or a service split. Employers retain training and personnel decisions. Market evidence (HRD Corp's RM2.62bn 2025 training approvals; 4.2m AI-exposed workers) is cited in the PRD.
<!-- answer:end final-5 -->

## 6. Final Submission Checklist

- [ ] The **actual deployed revision and snapshot** are accessible at the Section 1 URL; execute the six-must-have change test.
- [ ] Installation instructions work in an isolated environment.
- [ ] Team has identified official live-window commits relative to the 25 October 08:00 comparison point.
- [ ] Final pitch deck is exported as a flattened PDF and the exact final file is shared with judges.
- [ ] All fields, contact details, evidence, word limits and licence/disclosure statements are reviewed.

## 7. IP & Originality Declaration

### 7.1 Pre-Existing / Prior-Owned Work

**Team-leader record from 25 October: No**, Adept implementation was made for the hackathon; the separate KerjaCerdas project was consulted only for general security ideas, not imported. **Selection for organiser form: [ ] Yes [ ] No [ ] No change from Phase 1 — LEADER TO CONFIRM.** Reconfirm each member's prior code/design/research and any Phase 1 declaration before selecting. If Yes, identify the contributor, item and permissions privately; do not infer blanket originality from a repository history.

### 7.2 Third-Party Code, Datasets, or Models

**Yes**: third-party frameworks, curated public datasets and pre-trained models are used. **Selection: [x] Yes [ ] No [ ] No change from Phase 1.** Main classes of third-party resources, with terms requiring final legal review:

| Name | Type (code/dataset/model) | License / applicable terms |
|---|---|---|
| Next.js, React, Tailwind, next-intl, Recharts, FastAPI, Pydantic | code | Mainly MIT; check each package's installed notices. |
| PostgreSQL, pgvector, psycopg, PyMuPDF | code | PostgreSQL License; psycopg LGPL-3.0 (binary notices); PyMuPDF AGPL-3.0 or commercial licence — distribution review outstanding. |
| arXiv cs.AI metadata, US BLS baseline, O*NET 31.0, UN SDGs, OpenDOSM LFS, employer job feeds, provider courses | dataset | Separate source/provider terms; O*NET and OpenDOSM CC BY 4.0 with attribution; no blanket licence for job ads. |
| Sentence Transformers all-MiniLM-L6-v2; optional GLM-5.3/Gemini family | model | MiniLM Apache-2.0; hosted model/provider terms for GLM/Gemini to be checked. |
| Synthetic personas, curated skills/roles/course links and SDG alignments | dataset | Team-created parts, underlying provider/taxonomy rights retained; not official UN endorsement. |

### 7.3 Employment-Related IP Conflicts

**Selection: [ ] Yes [ ] No [ ] No change from Phase 1 — EACH MEMBER TO CONFIRM PRIVATELY.** No member's employment/internship/consulting terms were reviewed. If Yes, the leader must disclose the member, agreement and permission in the private organiser submission.

## 8. Declaration

**Unsigned draft.** Only the leader can attest to originality and the official hacking window after reviewing the team's records. **Signature: [leader to sign privately]. Date: [actual signing date].** This public PDF does not impersonate a signed organiser submission.
