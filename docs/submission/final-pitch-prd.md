# Adept — Product Requirements Document

Sourced skills-gap and reskilling planning for Malaysian employers and learners

**Product:** Adept

**Team:** Pecel Lele

**Competition:** SDC XMUM Hackathon 2026 · Domain 1: The Aiversecity Future-Ready Workforce

**Date:** 1 November 2026 · **Version:** 1.0 (finalist submission)

## 1. Executive summary

Adept helps an employer's learning-and-development (L&D) manager and each consenting employee decide **which skills to develop for a chosen role, in which order, and at what estimated time and cost**. Every recommendation is resolved against a curated catalogue of skills, roles and courses, carries its sources and snapshot date, and is labelled as an estimate wherever it depends on a forecast.

| Item | Summary |
|---|---|
| Problem | Malaysian employers already spend heavily on training (HRD Corp approved RM2.62bn of training assistance in 2025 [S1]), while 4.2 million workers are highly exposed to generative AI [S6]. Managers still choose courses before the skill gap behind a role is explained and documented. |
| Solution | A web platform with an **individual mode** (skills profile, explained role matches, ordered course plan, SDG links) and an **organisation mode** (consent-gated team gap view, programme proposals, progress review), plus the Adi help assistant. |
| First buyer | HR/L&D teams in HRD Corp-registered, mid-size Malaysian employers with AI-exposed operations staff (finance, shared services, GBS). TVET and university career centres are the second segment. |
| Business model | Per-active-seat subscription; test price **RM6 per seat per month**, with a RM10 manager/evidence tier. Prices are hypotheses to be validated in a paid pilot. |
| Differentiation | No invented entities (catalogue-ID validation), an openly documented scoring formula, Malaysia-specific sources, and two-sided consent between learner and employer. |
| Status | Working prototype on Replit with managed PostgreSQL; 142 skills, 48 roles and 104 courses in the curated catalogue; 15/15 automated synthetic journeys passed in local tests [A1]. Human trials and commercial validation are the next milestone. |
| Ask | One Malaysian operations team for an 8–12-week, 25–50-seat paid pilot. |

Adept is decision support. It does not hire, fire, promote or certify anyone, and it does not replace an HR management system.

## 2. Problem and opportunity in Malaysia

### 2.1 Training budgets already exist

| Finding | Source | Class |
|---|---|---|
| HRD Corp approved **RM2.62bn** in training assistance in 2025 (+32%), covering more than 2.8 million training places; RM130m and more than 103,000 places in IR4.0/digital training | HRD Corp media release, 13 Jan 2026 [S1] | Official |
| Covered employers pay a **1% levy on wages** (employers with ten or more Malaysian employees; 0.5% voluntary for five to nine) | HRD Corp employer registration [S2] | Official |
| More than 100,000 registered employers and more than 4.8 million registered workers | NST, Aug 2025 [S3] | Secondary |
| RM2.5bn levy collected and RM2.44bn grants disbursed in FY2025 | The Edge, relaying HRD Corp financial report [S17] | Secondary |
| 12.63 million employees out of 16.87 million employed persons; unemployment 2.9% (Aug 2026) | DOSM Labour Force Statistics, 9 Oct 2026 [S4] | Official |
| Median monthly salary **RM2,940** (2025) | DOSM Salaries & Wages Survey, 21 Sep 2026 [S5] | Official |
| 8.09 million persons (48.7% of employment) work in MSMEs; 1,069,831 MSME establishments | DOSM MSME Performance 2025 [S15]; Economic Census 2023 [S16] | Official |

### 2.2 The workforce is under pressure to reskill

| Finding | Source | Class |
|---|---|---|
| **4.2 million workers (28%)** highly exposed to generative AI, plus 2.5 million medium-high; women, young, clerical and urban workers are most exposed. Exposure is not job loss | ISIS Malaysia & World Bank, Jul 2025 [S6] | Official research |
| **About 620,000 jobs (18%)** in ten sectors highly impacted by AI, digital and green change within 3–5 years; 32% in global business services | The Edge on TalentCorp study, Nov 2024 [S7] | Secondary |
| Graduate skill-related underemployment **32.2% (1.60 million)**; **66.0%** for graduates aged 24 or below | DOSM Graduates Statistics 2024 [S8] | Official |
| MyCOL 2024/2025 lists **66** critical occupation groups | TalentCorp [S9] | Official |
| National AI Action Plan 2026–2030 targets up to **300,000** new AI roles by 2030 | NST, 22 Oct 2026 [S10] | Secondary |
| 117,733 PERKESO Employment Insurance job seekers re-employed between January and 14 August 2026 | Bernama, 18 Oct 2026 [S11] | Secondary |
| Employee attrition **18.2%** (2025); 2026 salary budgets +4.8% | Aon, 11 Dec 2025 [S12] | Secondary |

### 2.3 The gap Adept addresses

Training money and reskilling pressure are both visible. The decision between them is not: a manager typically combines a spreadsheet, an adviser, a course portal and an HRMS training module, and the reason a particular course was chosen for a particular role is rarely recorded. Adept targets this **pre-purchase training decision** by naming the role, weighting the skill gap, comparing sourced courses within budget and prerequisites, and keeping a record of why the plan was chosen and whether the employee accepted it.

Training spend and workforce scale establish context, not Adept's own demand. Buyer demand will be established through interviews, purchase orders and renewals (Section 10).

## 3. Target users and buyers

| Persona | Need | Evidence of need | Role in business model |
|---|---|---|---|
| P1 Working adult in clerical/GBS work facing AI exposure | Find a realistic adjacent role and the shortest credible learning path | ISIS 4.2m exposed [S6]; TalentCorp 620,000 impacted jobs [S7] | Learner (seat) |
| P2 Fresh graduate | Turn a degree into skills employers ask for | 66.0% underemployment for graduates aged 24 or below [S8] | Learner (free individual use) |
| P3 Career switcher | Compare target roles and the time/cost to switch | 18.2% attrition [S12]; PERKESO re-employment [S11] | Learner (free individual use) |
| P4 HR/L&D manager | Fund training against an explained, documented gap | RM2.62bn approved training assistance [S1] | **First buyer** |
| P5 TVET/university career adviser | Evidence-backed advising and course plans for a cohort | 1,996 TVET institutions [S13]; 65 private universities, 38 university colleges and 252 colleges [S14] | Second buyer |

**Primary buyer.** The head of L&D (with department finance) in a Malaysian operations employer. The employer pays; each employee controls their own plan and what they share.

**Why HR would buy.**

1. Direct levy-funded training toward a named, sourced gap for a named role.
2. Plan toward courses flagged as HRD-claimable; HRD Corp e-learning claims are hour-based, with a minimum of one hour and one complete module [S18].
3. Support internal mobility at a time of 18.2% attrition [S12].
4. Use consent-gated data with no protected attributes in ranking and no automated hiring or firing decisions.

Whether an Adept subscription itself is HRD-claimable is not established. Vendor material reports that pre-approved LMS subscriptions from registered providers can be claimable [S20]; Adept will test this through training-provider registration [S19] or bundling with registered providers.

## 4. Product overview and key features

### 4.1 Individual mode (`/app`)

- **Skills profile.** The learner uploads a CV (PDF, DOCX or text) or completes a form. Skills are extracted against the catalogue and the learner confirms each one; the CV file is parsed in memory and not stored.
- **Explained role matches.** Each target role shows a fit score, the skills that match, the weighted gaps, and plain-language **"what would raise this score"** tips instead of raw score arithmetic.
- **Reskilling pathway.** An ordered course plan that respects prerequisites, budget and available hours, showing estimated hours and cost per course. Gaps with no qualifying course remain visible rather than being filled with an invented course.
- **Scenarios.** Moderate and Fast AI-adoption scenarios change trend-based estimates with visible assumptions.
- **SDG links.** Roles and skills show curated links to UN SDG targets (mainly SDG 4, with SDG 5, 8, 9 and 10) as enabling reasons, not measured outcomes.

### 4.2 Organisation mode (`/org`)

- Managers invite members to a workspace; membership and manager permissions are enforced on the server.
- A **team gap heatmap** aggregates only skills that members have explicitly chosen to share, with small-cohort suppression to prevent identifying individuals.
- Managers propose training programmes; **members accept or decline** each programme, and managers review consented progress.
- Personal plans and assistant conversations remain private to the learner.

### 4.3 Future Skills Radar

The Radar page shows **signal cards and role-direction cards** built from dated AI-research signals (arXiv cs.AI publication activity) combined with a versioned US BLS projection baseline and curated exposure estimates. Trend signals also feed 25% of each role-fit score. Trend-line, range-chart and snapshot-comparison views are **future work**, planned once a verified refresh cadence produces enough fresh snapshots. All trend values are labelled as estimates; they are proxies, not Malaysian vacancy forecasts.

### 4.4 Adi assistant

Adi answers how-to questions about the product from a set of **fixed, reviewed answer blocks** written by the team. The default configuration uses no language model. When a model is enabled (RunPod-hosted GLM-5.3, with Gemini failover), it may only **select answer-block IDs** from an allowlist; unknown IDs or provider outages fall back to the deterministic guide. No unchecked model text is shown to users.

### 4.5 Sources and transparency

Every recommendation card shows one small **Sources** link, its snapshot date and estimate label; the full source list, model disclosure and methodology are on the **Data and AI use** page (`/about`). The interface is available in English, Malay and Chinese.

### 4.6 Core journey

1. A synthetic CV or form produces skills the learner confirms.
2. Research and job sources show their observation, retrieval and snapshot dates.
3. Role scores and gaps change when the profile changes.
4. The ordered plan resolves every course and skill to the catalogue and shows hours, cost and uncovered gaps.
5. Role and skill SDG target links are shown as enabling reasons.
6. Switching between Moderate and Fast scenarios changes estimates with visible assumptions.

## 5. Requirements

### 5.1 Functional requirements

| ID | Requirement | Acceptance criterion |
|---|---|---|
| FR-1 | Create a skills profile from CV upload or form, with learner confirmation | Only catalogue skills can be confirmed; unknown phrases produce suggestions that need confirmation |
| FR-2 | Rank target roles with an explained score and weighted gaps | Changing a profile changes the ranking or gaps; each role resolves to a catalogue record |
| FR-3 | Generate an ordered, prerequisite-aware course plan within budget and hours | Every course ID resolves; uncovered gaps are reported, never filled with invented courses |
| FR-4 | Show Moderate and Fast scenario estimates | Scenario switch changes trend-based estimates; values carry an estimate label |
| FR-5 | Show curated SDG target links for roles and skills | Target text comes from the UN SDG source; links are labelled as team-curated alignments |
| FR-6 | Organisation workspaces with invitations, consent-gated aggregates and programme proposals | Non-members are denied; missing consent is treated as no consent; small cohorts are suppressed |
| FR-7 | Members accept or decline employer programmes and control sharing | No programme is assigned without member acceptance |
| FR-8 | Adi answers product how-to questions | Only reviewed answer blocks are displayed; provider failure falls back deterministically |
| FR-9 | Shared, scheduled refresh of research, job and course sources | One bounded job per cadence for all tenants; validated, dated snapshots; stale or fallback data is labelled |
| FR-10 | Account data export and deletion | Learner can export and delete their account data |

### 5.2 Non-functional requirements

| Area | Requirement |
|---|---|
| Grounding | No invented jobs, courses, skills, statistics or SDG targets. Any model-assisted selection passes ID validation against a request-scoped allowlist, with deterministic fallback. |
| Attribution | Every recommendation, match score and trend projection carries sources (name, URL, retrieval date), snapshot date, scenario and an `is_estimate` flag; an automated regression test checks this on recommendation endpoints. |
| Privacy and consent | Server-side authentication, membership and manager checks; explicit opt-in for skill and progress sharing; CVs parsed in memory and not retained; contact details redacted from skill phrases sent to optional embedding suggestions. The competition prototype uses synthetic people only. |
| Human in the loop | Outputs support human judgement only; no autonomous hiring, firing, promotion or admission decisions. |
| Fairness | No age, gender, identity or protected-background attributes in ranking; fairness regression tests are maintained. |
| Security | Signed HTTP-only session cookies, upload type and size limits, bounded outbound requests with SSRF protection, exact CORS origins, fail-closed production startup checks. |
| Cost and performance | No model inference on page views; matching and pathways are deterministic database reads. Source refresh is a shared job, not per user. |
| Localisation | English, Malay and Chinese with key-parity checks. |

## 6. System architecture

A single public **Next.js 16** server presents learner, employee and manager views and proxies requests to a private **FastAPI (Python 3.11)** service. Accounts, profiles, memberships, the reference catalogue, dated snapshots, plans and progress are stored in **Replit-managed PostgreSQL** (PostgreSQL 16 with pgvector locally and in CI).

A daily GitHub Actions schedule sends an authenticated trigger to the deployed application. The application's own worker, holding a database advisory lock, fetches bounded public sources (arXiv submissions, documented job feeds, provider course pages, DOSM context), encodes research text with an **all-MiniLM-L6-v2** model on RunPod Serverless, validates provenance and publishes a dated snapshot atomically. Stored signals can be rescored without another model call.

| Stage | Method |
|---|---|
| Data sources | arXiv cs.AI [S34], US BLS 2023–2033 projections [S35], O*NET 31.0 [S36], UN SDG API [S37], OpenDOSM labour force [S38], MyCOL [S9], public job feeds and provider course catalogues |
| Cleaning | Bounded sampling, deduplication, date and coverage checks |
| Features | Catalogue-ID mapping, research mention counts and sentence embeddings |
| Method | Documented heuristic scoring and Moderate/Fast scenarios |
| Evaluation | Finite-value, coverage, date and ID validation before publication |
| Serving | Dated database snapshots read by deterministic APIs and sourced UI cards |

**Role-fit formula** (documented in the open-source repository; users see plain-language tips rather than the arithmetic): `fit = 0.45 × skill_overlap + 0.25 × trend_fit + 0.30 × interest_fit`, where skill overlap is importance-weighted and capped at the required level. An optional SDG slider `w` blends in an SDG component: `fit_sdg = (1 − w) × fit + w × sdg_impact`.

**Model disclosure.** all-MiniLM-L6-v2 (Apache-2.0) for research embeddings; optional GLM-5.3 and Gemini models for Adi answer-block selection; optional `gemini-embedding-001` for unfamiliar-skill suggestions. The default runtime setting uses no language model.

## 7. Differentiation and competitive landscape

| Product | Price signal | What it does | Adept's position |
|---|---|---|---|
| LinkedIn Learning Teams | US$379.88 per licence per year [S21] ≈ RM128/month at BNM USD selling rate 4.056 (30 Oct 2026) [S22] (estimate) | Content library | Decision layer that points to free and paid courses across providers |
| Coursera for Teams | About US$399 per user per year (third-party) [S23]; enterprise pricing custom [S33] | Content library | As above |
| Workday Skills Cloud | Quote-only, sold within HCM suite [S24] | Enterprise skills ontology | Malaysia-specific sources, sized for mid-size employers |
| BrioHR | RM3 training / RM7 Talent Essentials / RM21 All-in-One per employee per month; RM200 minimum [S25] | HRMS training administration | Decides *which* gap and course to fund, then exports to existing administration |
| Swingvy | RM8.50 per user per month, five-user minimum [S26] | HR and payroll suite | Complements; no duplicated HR administration |
| MyFutureJobs, UpskillMalaysia, MyMahir | Free public portals [S27] | Job and programme matching | Adds a person-level explained gap and a consented team view |
| Generic chatbot + spreadsheet | Low cost | Drafts generic advice | Validated catalogue IDs, dated sources, consent and an auditable decision record |

**Defensibility to build.** (1) A grounded, no-invention catalogue: in local automated tests, 15/15 synthetic journeys passed checks that every planned course and skill ID resolves to a sourced catalogue record [A1]. (2) An explainable, openly documented scoring formula. (3) Malaysia-specific data plumbing: MyCOL, DOSM, Malaysian job feeds, MYR pricing and HRD flags. (4) A two-sided individual and organisation model with explicit consent. Over time, the reviewed catalogue, source history and buyer workflow integration are the assets that compound; a formula alone is not a moat.

## 8. Business model and pricing

| Element | Design |
|---|---|
| Customer | Employer HR/L&D (first); TVET and university career centres (second, flat institutional licence) |
| Unit | Active paid learner seat per month |
| Test price | **RM6 per seat per month** (about 0.2% of the RM2,940 median monthly salary [S5]); **RM10** for a deeper manager/evidence tier |
| Individual use | Free and bounded, for discovery and learning; no consumer revenue is assumed |
| Funding route to test | Ordinary L&D software budget first; HRD claimability via training-provider registration or bundling [S19] |
| Pricing validation | Paired written quotes to ten eligible buyers; a paid pilot invoice rather than a survey; refusals and procurement objections recorded |

RM6 is set below BrioHR's RM7 Talent Essentials bundle [S25] because Adept is positioned as an add-on decision layer, not a full HR suite. Neither RM6 nor RM10 has yet been validated with buyers.

**Pilot unit economics (illustration).** A 40-seat, three-month pilot at RM6 bills `40 × RM6 × 3 = RM720`, recognised at RM240 per month. Assuming three support and review hours per organisation per month at RM50 per hour (RM150), the contribution is RM90 per month before hosting, data rights, inference, billing fees and sales. Break-even customers are `ceil(F / (RM240 − v))` where `v` is monthly delivery cost per customer and `F` is fixed monthly cost; both will be measured in the pilot.

## 9. Market sizing and financial projection

### 9.1 TAM, SAM and SOM (estimates)

All values use RM72 per seat per year (RM6 × 12).

| Measure | Basis | Estimate |
|---|---|---|
| TAM | 4.8 million HRD-registered workers [S3] × RM72 | **≈ RM345.6m per year** (cross-check: 4.2 million AI-exposed workers [S6] × RM72 ≈ RM302.4m) |
| SAM | About 620,000 highly impacted jobs [S7] × RM72 | **≈ RM44.6m per year** |
| SOM (year 5, base case) | 30,000 seats (4.8% of SAM seats) plus institution licences | **≈ RM3.5m per year** |

These are top-down estimates. Registered workers and impacted jobs are not paid seats, and an official Malaysian HR/L&D software market size was not found (paid reports such as IMARC's Malaysia IT-training estimate [S31] have undisclosed methods and are not used). The bottom-up check that will replace these estimates is `qualified employers × seats per employer × price × 12`, built from a qualified buyer roster and observed win rates. As an illustration, if 1,000 organisations qualify with 40 seats each at RM6, the serviceable market would be RM2.88m per year; three won 40-seat accounts would produce RM8,640 per year.

### 9.2 Five-year projection (base case, estimate)

Revenue = employers × seats × price × 12 + institutions × flat licence. Price RM6 per seat per month in 2027 and a blended RM8 thereafter; institution licence RM20,000 (2028–29) and RM25,000 thereafter. Costs: team at an assumed RM6,000 per month loaded per FTE (2, 4, 6, 9 and 12 FTE); infrastructure assumed at US$117, 400, 1,000, 2,500 and 5,000 per month converted at 4.056; sales and partner cost at 20% of revenue.

| Year | Employers × seats | Institutions | Revenue (RM) | Team + infra + sales (RM) | Operating result (RM) |
|---|---|---|---:|---:|---:|
| 2027 | 5 × 50 | 0 | 18,000 | 153,295 | −135,295 |
| 2028 | 20 × 60 | 3 | 175,200 | 342,509 | −167,309 |
| 2029 | 60 × 80 | 8 | 620,800 | 604,832 | 15,968 |
| 2030 | 150 × 100 | 15 | 1,815,000 | 1,132,680 | 682,320 |
| 2031 | 300 × 100 | 25 | 3,505,000 | 1,808,360 | 1,696,640 |

- **Sensitivity:** a low case (half the customers) reaches RM1.74m revenue in 2031; a high case (1.5×) reaches RM5.27m.
- **Funding need:** cumulative pre-break-even need in the base case is about **RM0.30m** (estimate).
- **Share required:** 300 employers in year 5 is 0.3% of more than 100,000 registered employers [S3].
- **Why the cost curve is favourable:** reads are deterministic, so there is no model cost per page view; one shared daily refresh serves all customers; and the catalogue and Malaysian sources are reused across customers. Marginal cost per seat is mainly support time.
- **Spending gates:** paid pilot → renewal → HRD claimability answer → measured capacity.

## 10. Pilot plan and success metrics

**Design.** One Malaysian operations employer, one role family, one training budget, 25–50 seats, 8–12 weeks. The competition prototype uses synthetic data; a real-data pilot requires signed employer and learner consent, a privacy notice, a data-processing agreement, a retention and deletion plan, an access audit and a security review. The baseline is the manager's current spreadsheet and course-buying process on matched cases, with Adept-first and manual-first order counterbalanced. An independent reviewer rates plan validity.

**Recruitment.** Discovery conversations with 10–15 Malaysian operations L&D decision-makers, leading to one pilot partner.

| KPI | Current evidence | Pilot target |
|---|---|---|
| Catalogue-ID validity of recommended courses | Phase 1 target 100%; 15/15 automated synthetic journeys passed ID-resolution checks locally [A1] | 100% in an independent audit |
| Median time from intake to a valid plan | Phase 1 target under 3 minutes; human trials not yet run | Under 3 minutes (human-completed) |
| Plans rated valid by an independent reviewer | Not yet measured | ≥ 80% |
| Median manager decision time vs manual baseline | Not yet measured | ≥ 20% improvement |
| Consented intake completion | Not yet measured | ≥ 70% |
| Commercial signal | No paid customers yet | ≥ 1 paid renewal offer |
| Privacy incidents | — | 0 (any incident stops the pilot) |

Later metrics are verified skill demonstration by an independent assessor, repeat use and paid renewal. Course clicks are not treated as proof of proficiency, redeployment or job placement. A buyer who will not pay or renew after a valid workflow triggers a narrower proposition.

## 11. Scalability and feasibility

**Replit-first.** The prototype runs as one public web server, one private API and one managed PostgreSQL instance with explicit pool limits and indexes. Source refresh is a single shared job with a lock, lease, retry and recovery; page reads use stored snapshots. This keeps the marginal cost of a learner low: a 30-day research refresh is charged once per shared run, not once per learner.

**Scale path.** Capacity has not yet been load-tested. Adept will measure database p95 query time and pool saturation, active connections against the plan cap, lock contention, storage growth, restore time, cache age and worker recovery, and will add workers or split services only when measured thresholds are reached.

**Public provider tariffs (USD, retrieved 31 Oct 2026).**

| Service | Tariff | Source |
|---|---|---|
| Replit Autoscale | $1/month base + $0.40 per million requests + $0.60 per million compute units; egress $0.05/GiB | [S28] |
| Replit PostgreSQL | $0.16 per compute-hour + $0.35 per GiB-month | [S28] |
| RunPod Serverless (MiniLM) | L4/24GB $0.75 per GPU-hour; RTX 4090 $1.34; billed per running second, rounded up per period | [S29] |
| Gemini embedding / Flash Lite | $0.15 per million input tokens (batch $0.075); Flash Lite $0.30 input + $2.50 output per million tokens | [S30] |

**Illustrative monthly model and database cost (assumptions, not invoices).** 720 database compute-hours with 5 GiB stored ≈ US$116.95; 30 daily MiniLM jobs × 2 periods × 90 s on L4 ≈ US$1.13; 200 embedding searches × 100 tokens ≈ US$0.003; 300 Adi requests with 5% Gemini fallback ≈ US$0.03 (primary GLM endpoint cost to be measured). Hosting compute units, licences and human support are additional and are expected to dominate.

**Workload scenarios (planning assumptions).** 50 seats per organisation, 80% monthly active, per active user per month: one saved plan, two role checks, four trend-backed role reads, 0.2 skill searches and 0.3 Adi chats; three support hours per organisation per month at RM50.

| Monthly active users | Organisations / paid seats | Plans / role checks / role reads | Searches / Adi chats | Revenue at RM6 | Support cost assumption |
|---|---:|---:|---:|---:|---:|
| Pilot (32) | 1 / 40 | 32 / 64 / 128 | 6.4 / 9.6 | RM240 | RM150 |
| 1,000 | 25 / 1,250 | 1,000 / 2,000 / 4,000 | 200 / 300 | RM7,500 | RM3,750 |
| 10,000 | 250 / 12,500 | 10k / 20k / 40k | 2k / 3k | RM75,000 | RM37,500 |
| 100,000 | 2,500 / 125,000 | 100k / 200k / 400k | 20k / 30k | RM750,000 | RM375,000 |

Source refresh stays at about 30 shared daily checks at every scale, rather than one refresh per user. At 2,500 organisations, support staffing (not compute) is the binding constraint, which is why onboarding and review tooling are on the roadmap.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Trend signals are proxies (research attention, US baseline), not Malaysian vacancy data | Labelled as estimates with sources and dates; scenarios show assumptions; Malaysian job and labour data shown with their own scope |
| Automatic refresh not yet verified in production | Apply migrations and configuration, record a successful live publication and a later scheduled run; stale or fallback data is labelled in the UI |
| Catalogue facts (fees, dates, prerequisites) change | Dated course records, reviewer checks during the pilot, uncovered gaps shown explicitly |
| Buyers may not pay above incumbent HR modules | Add-on pricing below incumbent bundles; paid pilot and renewal as the gate before scaling |
| HRD claimability of the subscription is unconfirmed | Sell from software budget first; test training-provider registration or bundling |
| Personal data in a real pilot | Consent, data-processing agreement, retention plan, access audit and security review before any real data; synthetic data in the competition |
| Model misuse or invented content | Models only select validated IDs; deterministic fallback; no model text displayed |
| Support load at scale | Measure hours per organisation in the pilot; build onboarding and review tooling before growth |
| Third-party licences (e.g. PyMuPDF AGPL, job-feed reuse terms) | Licence review before commercial distribution; commercial licence or replacement if required |

## 13. Roadmap and future work

| Horizon | Milestones |
|---|---|
| Now (submission) | Individual and organisation modes, explained matching and gaps, catalogue-grounded pathways, SDG links, Radar signal and role-direction cards, Adi answer blocks, sources on every card, three languages |
| Next 30 days | Verify the deployed revision and a live source publication; ten buyer discovery interviews; billing instrumentation and a backup-restore drill |
| Next 90 days | One 25–50-seat paid pilot under consent and contract; independent plan review; renewal decision |
| Future work | Radar trend-line, range and snapshot-comparison charts once refresh cadence is verified; exportable training decision record; HRIS import, SSO and BI export when requested by a paying buyer; TVET/university workflow; HRD training-provider route |

**Out of scope.** Predicting exact job losses, automated hiring or personnel decisions, certificate equivalence, and model calls on every page view.

## 14. Sources

All web sources were retrieved on 31 October or 1 November 2026 unless another date is given. Live pages may change after retrieval.

- **S1** HRD Corp, Media Release: Highlights of 2025, 13 Jan 2026. https://hrdcorp.gov.my/wp-content/uploads/2026/01/Media-Release-Highlights-of-2025.pdf (retrieved 1 Nov 2026)
- **S2** HRD Corp, Employer Registration. https://hrdcorp.gov.my/employer/ (retrieved 31 Oct 2026)
- **S3** New Straits Times, HRD Corp registers over 4.8mil employees, 100,000 employers, Aug 2025. https://www.nst.com.my/news/nation/2025/08/1263966/hrd-corp-registers-over-48mil-employees-100000-employers-says-steven (retrieved 31 Oct 2026)
- **S4** DOSM, Labour Force Statistics, August 2026, 9 Oct 2026. https://www.dosm.gov.my/portal-main/release-content/labour-force-statistics-aug2026 (retrieved 1 Nov 2026)
- **S5** DOSM, Salaries & Wages Survey Report 2025, 21 Sep 2026. https://www.dosm.gov.my/portal-main/release-content/salaries-and-wages-survey-report- (retrieved 1 Nov 2026)
- **S6** ISIS Malaysia & World Bank, Novel AI technologies and the future of work in Malaysia, Jul 2025. https://www.isis.org.my/2025/07/06/novel-ai-technologies-and-the-future-of-work-in-malaysia/ (retrieved 1 Nov 2026)
- **S7** The Edge Malaysia, report on TalentCorp impact study, Nov 2024. https://theedgemalaysia.com/node/734414 (retrieved 1 Nov 2026)
- **S8** DOSM, Graduates Statistics 2024, 31 Oct 2025. https://www.dosm.gov.my/uploads/release-content/file_20260401145140.pdf (retrieved 1 Nov 2026)
- **S9** TalentCorp, MyMahir Malaysia Critical Occupations List (MyCOL) 2024/2025. https://www.talentcorp.com.my/resources/publications/mymahir-malaysia-critical-occupations-list-mycol20242025/
- **S10** New Straits Times, Malaysia targets 300,000 AI jobs by 2030, 22 Oct 2026. https://www.nst.com.my/amp/business/economy/2026/10/1561294/malaysia-targets-300000-ai-jobs-2030 (retrieved 1 Nov 2026)
- **S11** Bernama, PERKESO EIS re-employment, 18 Oct 2026. https://bernama.com/en/general/news.php?id=2621984 (retrieved 1 Nov 2026)
- **S12** Aon, Aon survey projects 4.8 percent salary growth for Malaysia in 2026, 11 Dec 2025. https://www.aon.com/apac/in-the-press/asia-newsroom/2025/aon-survey-projects-4-8-percent-salary-growth-for-malaysia-in-2026 (retrieved 1 Nov 2026)
- **S13** National TVET Portal, institution counters (895 public, 52 state/statutory, 1,049 JPK private). https://www.tvet.gov.my/ (retrieved 31 Oct 2026)
- **S14** MIDA, Education Services, Feb 2026. https://www.mida.gov.my/industries/services/education-services/ (retrieved 1 Nov 2026)
- **S15** DOSM, MSME Performance 2025, 30 Jul 2026. https://www.dosm.gov.my/portal-main/release-content/micro-small--medium-enterprises-msmes-performance-2025 (retrieved 31 Oct 2026)
- **S16** DOSM, Economic Census 2023: Profile of SMEs, 19 Sep 2024. https://www.dosm.gov.my/portal-main/release-content/economic-census-2023-profile-of-small-and-medium-enterprises (retrieved 31 Oct 2026)
- **S17** The Edge Malaysia, HRD Corp FY2025 financials. https://theedgemalaysia.com/node/809678 ; HRD Corp Financial Report 2025. https://hrdcorp.gov.my/wp-content/uploads/2026/07/HRD-Corp-Financial-Report-2025-Digital-Version.pdf (retrieved 31 Oct 2026)
- **S18** HRD Corp Support Centre, e-learning programme financial assistance. https://supportcentre.hrdcorp.gov.my/portal/en/kb/articles/e-learning-programme-financial-assistance (retrieved 1 Nov 2026)
- **S19** HRD Corp, training provider registration and claimable courses. https://supportcentre.hrdcorp.gov.my/portal/en/kb/articles/training-provider-registration ; https://hrdcorp.gov.my/hrdcorp-claimable-courses (retrieved 31 Oct 2026)
- **S20** Disprz (vendor blog), HRDF digital learning LMS Malaysia. https://disprz.ai/blog/hrdf-digital-learning-lms-malaysia (retrieved 1 Nov 2026)
- **S21** LinkedIn Help, LinkedIn Learning pricing. https://www.linkedin.com/help/learning/answer/a768297 (retrieved 1 Nov 2026)
- **S22** Bank Negara Malaysia, exchange rate API (USD selling rate, 30 Oct 2026). https://api.bnm.gov.my/public/exchange-rate/USD
- **S23** TrainingCost (third party), Coursera for Business pricing. https://trainingcost.com/coursera-for-business-pricing (retrieved 1 Nov 2026)
- **S24** Gartner Peer Insights, Workday Skills Cloud. https://www.gartner.com/reviews/product/workday-skills-cloud (retrieved 1 Nov 2026)
- **S25** BrioHR, Malaysia pricing plans. https://briohr.com/pricing-plans-my/ (retrieved 31 Oct 2026)
- **S26** Swingvy, Malaysia pricing. https://www.swingvy.com/my/pricing (retrieved 31 Oct 2026)
- **S27** MyFutureJobs https://myfuturejobs.gov.my/ ; UpskillMalaysia https://upskillmalaysia.gov.my/aboutusp (retrieved 31 Oct 2026)
- **S28** Replit, August 2026 cloud billing updates. https://docs.replit.com/billing/aug-cloud-billing-updates (retrieved 31 Oct 2026)
- **S29** RunPod, pricing and Serverless billing. https://www.runpod.io/pricing ; https://docs.runpod.io/serverless/pricing (retrieved 31 Oct 2026)
- **S30** Google, Gemini API pricing. https://ai.google.dev/gemini-api/docs/pricing (retrieved 31 Oct 2026)
- **S31** IMARC, Malaysia IT training market (USD 347.1m, 2025; not used for sizing). https://www.imarcgroup.com/malaysia-it-training-market
- **S32** Hays, Asia Salary Guide 2025 (56% AI use, 26% training in Malaysia; cited in Phase 1, survey table not yet verified). https://www.hays.com.my/hays-asia-salary-guide-2025
- **S33** Coursera for Business and Degreed pricing pages (custom pricing). https://www.coursera.org/business/compare-plans ; https://degreed.com/experience/pricing/ (retrieved 31 Oct 2026)
- **S34** arXiv API. https://info.arxiv.org/help/api/
- **S35** US Bureau of Labor Statistics, occupational projections 2023–2033. https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm
- **S36** O*NET Resource Center (O*NET 31.0, CC BY 4.0). https://www.onetcenter.org/
- **S37** UN Statistics Division, SDG API. https://unstats.un.org/SDGAPI/v1/sdg/Goal/List
- **S38** OpenDOSM, monthly Labour Force Survey (CC BY 4.0). https://data.gov.my/data-catalogue/lfs_month

## Appendix A. Prototype evidence

- **A1 — Automated synthetic journeys.** An isolated local test run on 30 Oct 2026 completed 15/15 scripted API journeys across five synthetic profiles, with per-persona median machine times of 0.091–0.236 seconds, using a historical fixture. It excludes browser time, human review, network and paid models, and is not a human time-to-plan result. Human timed trials: 0 attempted to date.
- **A2 — Catalogue size.** Source catalogue at the reviewed revision: 142 skills; 48 roles, of which 33 are target roles; 104 courses; 1,175 job-posting rows; 88 role-SDG and 167 skill-SDG alignment rows; UN definitions for 17 goals and 169 targets.
- **A3 — Sponsor proof of use.** Replit: hosting and database screens with a displayed US$6.38 account spend in one billing window. RunPod: an RTX 4090 Pod batch of 110 embeddings in 0.354 seconds and the Serverless MiniLM endpoint set-up. These are historical captures, not current per-learner costs.
- **A4 — Revision.** This document describes repository revision `0a7868c` (31 October 2026). The deployed prototype is at https://adept-my.replit.app and the source at https://github.com/pecel-lelele/adept.
