# Adept: Product PRD and Final Pitch Brief

**Audience:** Pecel Lele's product, design and pitch team. **Status:** evidence-based plan, reviewed 1 November 2026 against the 31 October `main` revision `0a7868c`. Research was retrieved 31 October unless otherwise dated. Public/synthetic competition data only. No live paid inference, production writes, interview, invoice or deployment test was conducted for this assessment. All evidence needed to understand the claims and calculations is stated below; external source titles and dates appear without links.

## Executive decision — what Adept is

**One sentence:** Adept helps an employer's L&D manager and each consenting learner decide **which sourced skills to develop for a chosen role, in which order and at what estimated time/cost**, while keeping dated AI-research signals and uncertainty visible. It is **not** an employer's hiring engine, a provider of professional certification, a calibrated Malaysian job-demand predictor, or an HRMS replacement.

**Initial paying customer hypothesis:** Malaysian HRD Corp-registered mid-size operations employers, beginning with one finance/shared-services/GBS training team; L&D buys and manages a cohort, learners control their own plans and sharing. An institution/TVET centre is a later possible buyer, and free individual use is discovery/learning rather than validated acquisition. This is a hypothesis to test with buyers, **not traction**. Avoid assuming HRD levy funds a SaaS subscription: HRD Corp's employer rules establish training contributions, not subscription claimability.

**The strongest defensible wedge to test:** the *training decision before purchase* — identify a named, weighted gap for a target role; compare sourced, prerequisite-aware programmes within budget; document why a manager chose a course and let the member accept. BrioHR already sells training **administration** for RM3 per month, Talent Essentials for RM7 and a RM200 minimum contract on its Malaysia pricing page. We must prove that decision quality/work saved is incremental to that, a spreadsheet and an adviser; no page-view count proves it.

### Five uncomfortable truths, ranked

1. **A deployed refresh is not evidenced.** The source includes an app-side durable scheduler/worker; activation still requires migrations, secrets, deployment, a successful publication and later scheduled run. Do not show a historical 2024 replay or a 2026-10-20 fixture as today's research.
2. **Our forecast is an estimate based on proxy inputs.** arXiv paper attention and US BLS projections do not establish Malaysian role vacancies or employment outcomes; Moderate/Fast transform stated assumptions. A role's outlook *level* and its *change over a selected interval* differ.
3. **The Phase 1 targets have not been shown in a human study.** The preliminary submission proposes 100% catalogue-ID validity and median synthetic-case intake-to-valid-plan under three minutes, not a 20% manual-time improvement. Human results: 0 attempts; 15 local scripted journeys are machine-only and use historical fallback.
4. **A catalogue row does not make a learner job-ready.** Today's CSV holds 142 skills, 48 roles (33 target flags) and 104 courses, but requirements and gains are curated; fee/date/prerequisite/eligibility can change. A clicked completion is not verified proficiency, certificate entitlement or placement.
5. **No commercial proof exists.** There are no evidenced buyers, paid pilots, renewal rate, support hours per organisation, RunPod worker-seconds, Replit bills allocable to Adept, or verified software claimability. Earlier RM15/RM25-seat ideas exceed local HR-suite bundles and must be tested, not asserted as a viable margin.

## Part I — product and implementation PRD

### 1. Users, purchase decision and jobs to be done

| Candidate | Decision-maker / payer | Returning workflow and existing alternative | Evidence/gap | Priority |
|---|---|---|---|---|
| Employer HR/L&D in AI-exposed operations | Head of L&D / department finance; employer pays | Each quarter: pick who to train for a selected role and what to fund. Today: manager spreadsheet + adviser + course portal + HRMS training module | HRD levy supports training budgets; BrioHR has a real incumbent module. No employer interviews/paid order | **First pilot** |
| TVET/university career centre | Career-services head / institutional procurement | Each cohort: evidence-backed advising and course plans; today: staff advisers, institutional LMS, UpskillMalaysia, job portals | National TVET portal lists institutions, not software buyers. Public procurement/integration and advisor validation are untested | Later |
| Individual worker/graduate | Person uses; individual or employer might pay | Reassess after a skills change; today: ChatGPT, MyFutureJobs, course search, adviser | Zero observed returning users or paid conversion; do not promise consumer revenue | Free, bounded pilot |

**Why a company could pay:** reduce the manager's time to a justified training choice and reduce wrong-course selections *if* an independent reviewer finds plans relevant and learners accept them. HCC reimbursements require actual rules/eligibility; do not promise they fund Adept. A paid renewal, documented workflow adoption, and independently reviewed outcome are the evidence gates. ChatGPT can draft generic advice cheaply; our proposed incremental value is catalogue-ID grounding, dated evidence, manager consent/approval/audit workflow and team-specific gap aggregation. Benchmark each against real buyer alternatives instead of assuming superiority.

### 2. Preliminary → final change narrative and status

`b34c06c` is the **last main commit before 25 October 2026, 08:00 MYT** (07:46:32). This cutoff already included five synthetic demonstration CVs, both sponsor proof PDFs, a signed-account root-hosted prototype and the preliminary proposal. It was **not** only a skeleton or a screenshot. The final source baseline above includes many merges from 30–31 October. The exact official 48-hour physical-sprint window remains **unknown**: do not label every change after this cutoff as sprint-built without the event timetable and commit evidence. The Phase 1 PDF proposed the end-to-end journey and two evaluation targets, but neither the preliminary screenshots nor repository code establishes a buyer outcome.

| Product / idea | Before 25 Oct 08:00 MYT (`b34c06c`) | Final source at pinned main | What remains to prove |
|---|---|---|---|
| Signal refresh | A working offline MiniLM/arXiv proof and dated snapshots; an early RunPod RTX 4090 Pod screenshot shows **110** vectors in **0.354 seconds for that one batch**. Not a continuous production ingestion KPI | The first GitHub-based refresh later failed against Replit's private database host; the design pivoted to GitHub as a clock and an authenticated **in-app** worker using its own managed-PostgreSQL connection. Durable runs, advisory lock, bounded source fetch, stored measured inputs, source-specific publication and stale states now exist | Apply approved production migrations/configuration, record a successful live publication and later scheduled success; do not call the Pod test the production worker speed |
| Trend interpretation | Dated Moderate/Fast skill trend snapshots and sourced radar existed. No role/category comparison timeline yet | Trend signals stay inside role matching (25% trend weight under Moderate/Fast). The **Future Skills Radar page ships with its signal and role-direction cards**; its **trend-line, range-chart and snapshot-picker cards are moved to future work** and removed from the shipped UI (parallel frontend PR); they return only after a verified fresh snapshot cadence | Capture a deployed selection/change test; avoid calling a research-share proxy observed Malaysian vacancies |
| Matching and learner journey | CV/form confirmation, deterministic role scoring/gaps, course ordering, curated SDG links and individual/organisation modes existed in the source; PDFs show early hosted infrastructure | Reworked score explanations and scenario deltas, added catalogue/critical-occupation scope notes, preserved guarded member sharing and improved task completion/empty/stale states. Curated records expanded to 142 skills, 48 roles (33 target flags) and 104 courses | Independently review course fit/availability and measure human plan validity; progress click is not verified proficiency |
| Operating model and customer | Two modes aimed at four personas, no prioritised paying buyer or validated willingness-to-pay | Product strategy **proposed in this brief**: one employer L&D training decision first; a shared Replit-first scheduler and database replace ad-hoc per-user inference assumptions. This is a positioning proposal, **not a shipped monetisation feature** | Buyer interviews, written price test, invoices, support costs and renewal decision; do not claim commercial pivot was deployed |
| Trust and deployment | Root-hosted UI/API and signed demo accounts with PostgreSQL; sponsor-use screenshots historical | One public Next.js/proxied private API, stronger attribution, workspace/consent regressions, generated contracts and source-date metadata; automatic refresh credentials now stay in the hosted app rather than GitHub's DB URL | Verify deployed SHA, authorised sharing, restoration, actual provider usage and licences |

**Core journey acceptance, judge-facing:** (1) synthetic CV/form gives confirmable catalogue skills; (2) research/job source shows *observation*, *retrieval* and *snapshot* dates; (3) matching score components/gaps change when the profile changes; (4) ordered plan resolves every entity and shows hours, cost and unmet gaps; (5) role **and** skill SDG target reasons show as enabling links, not outcome claims; (6) Moderate/Fast changes estimates with visible assumptions. Demonstrate an actual altered source snapshot changing a downstream output; a component visible in source is not a deployed change test. No real CVs.

### 3. Trace the claims, not just the component count

| User-visible belief | Actual source/logic and status | Risk / acceptance evidence |
|---|---|---|
| “Trend signals predict future Malaysian jobs” (Radar trend-line charts are future work) | Database-first trend read; labelled fixture fallback dated 13/20 October 2026. Public arXiv completed weeks, a versioned US BLS baseline and curated exposure produce estimates. The stored synthetic evidence uses 2024 research observations. **Implemented; deployment unverified.** | Show production run, measured period and method; say “AI-research signal / estimated role outlook,” not Malaysian jobs forecast |
| “Role recommendations fit me” | Deterministic score: 0.45 skill overlap + 0.25 trend fit + 0.30 interests, with optional SDG adjustment. The profile changes the result; roles come from a curated catalogue. **Locally tested; production unverified.** | Change a synthetic profile and show ranking/gap changes; one older fixture showed 0/5 top-five set changes across scenarios, not a universal result |
| “Courses close the skill gap” | Pathway engine selects ordered stored courses by coverage, budget and prerequisites. A course can partially cover a proficiency gap and its date/fee can age. **Dynamic plan over static, checked references.** | Resolve every ID; independently inspect level, budget, prerequisite and issuance terms; no claim of qualification |
| “My learning helps an SDG” | UN target definitions plus team-curated role/skill-to-target hypotheses. **Reference data by design.** | Compare choices by target; record real learning evidence separately from a displayed SDG badge |
| “Manager can see my skills” | Server-enforced membership/manager checks; explicit sharing consent and small-cohort suppression. **Locally tested; production unverified.** | Member denied other workspaces, missing consent is never consent, no tiny-cohort leakage |
| “Adi independently advises me” | Configured provider selects validated server-authored answer IDs; deterministic guide otherwise. **Source implemented; provider reachability unverified.** | Unknown IDs or outage fall back; no unreviewed model prose or inference on every page view |

Static official UN/O*NET tables are legitimate reference data; the error is calling a **stale observation current** or an **inferred outcome measured**.

### 4. Requirements and boundaries for commercial pilot

- **P0 — truthful evidence:** pin deployment SHA/build identity; verify original/retrieval/snapshot dates and refreshed publication; distinguish no data, zero and source outage; remove or relabel role-demand claims until Malaysian role-level validation exists. Acceptance: dated demo recording of all six must-haves and source-change propagation, a later automatic run, no silent fixture masquerade. Effort: 2–5 team days after host access; dependency: operator migration/secret setup, actual model budget.
- **P0 — buyer workflow:** manager chooses target role, approves budget/course plan, member explicitly accepts/shares, manager reviews evidence; export a human-readable decision record with source/fee/prerequisite date. Acceptance: 5 synthetic cohort sessions with permission/consent tests and review of every generated entity. Effort: 3–7 days; dependency: current org flow and catalogue review.
- **P1 — outcomes instrumentation:** reviewer-rated valid plan; human time-to-plan; course relevance/availability check; learner consent and verified skill evidence separate from completion clicks. Acceptance: pre-registered 8–12-week pilot protocol, raw anonymised numerator/denominator and fail counts. Effort: 2–3 days protocol plus pilot; dependency: ethical approval, privacy/legal agreement for any real data.
- **P1 — operation:** record job UUID, start/end, per-source changed rows, model billed seconds/tokens, DB pool use/latency, cache reuse; expiry, backup restore, low-evidence alert. Acceptance: alert exercise + restore on disposable data + cost export attributed to app. Effort: 4–10 days; dependency: account/plan telemetry and owner authorisation.
- **P2 — integrations only when won:** HRIS import, SSO, provider agreements, regulated credential verification, BI export. Acceptance: signed pilot request, permissions/licence review and measured support load before implementation. Effort: unknown until buyer spec; dependency: paid design partner. Do not expand generic chat or unvalidated role categories to simulate product-market fit.

**Replit-first operational invariant:** one managed PG instance with explicit pool limits and indexes, shared worker lock/lease/retry/recovery, bounded external calls and stored snapshots. A fresh browser read is cheap. A source refresh is a shared job. Measure pool saturation and query p95, active connections vs plan cap, lock contention, WAL/storage growth, restoration time, stale-cache age and worker recovery. “Replit cannot scale” is *not established*; whether a plan limit, DB plan setting or our SQL is the bottleneck is presently **unknown**. Do not migrate providers or split into microservices without observed thresholds.

### 5. Pilot protocol (not yet executed)

**Recruitment:** approach 10–15 Malaysian operations L&D decision-makers for discovery, then secure one company willing to pilot a single 25–50-person synthetic/demo workflow first. Any later real-data pilot needs signed employer/learner consent, privacy notice, legitimate processing agreements, retention/deletion plan, access audit, security review and legal guidance; competition materials remain synthetic. **Duration:** 8–12 weeks, one role family and one budget. **Baseline:** current manager spreadsheet/course-buying decision for matched cases with documented provenance and equivalent time/budget constraints; counterbalance Adept-first/manual-first. **Leading metrics:** fraction of plans independently valid, manager review minutes, learner acceptance, error/rework and source/link freshness; numerators and denominators tracked. **Later metrics:** verified skill demonstration by independent assessor, repeated use and paid renewal; do not infer redeployment, productivity or job placement from clicks. **Go/no-go assumptions:** illustrative targets ≥80% independently valid plans, ≥20% median *human* decision-time improvement vs matched manual baseline, ≥70% consented completion of intake and 1 paid renewal offer. All are new pilot gates, **not measured or Phase 1 targets**. A relevant-course disagreement or privacy incident stops the pilot; a buyer who will not pay or renew after a valid workflow forces a narrower proposition/pivot.

## Part II — Malaysia market and competitor evidence

### Research update, 1 November 2026 (implementation, scalability and feasibility focus)

Mentor feedback: judges set the problem and may invest, so lead with feasibility. This section supersedes older market wording where they differ. **Official** = government document read by the team; **Secondary** = press/vendor relay; **Estimate** = our arithmetic. No interviews, customers or revenue are claimed. Retrieved 1 Nov 2026 unless marked 31 Oct.

**Market and money already flowing**

| Finding | Source (publisher, date, URL) | Class |
|---|---|---|
| HRD Corp approved **RM2.62bn** training assistance in 2025 (+32%); **>2.8m** training places; RM130m and >103,000 places in IR4.0/digital | HRD Corp media release, 13 Jan 2026, https://hrdcorp.gov.my/wp-content/uploads/2026/01/Media-Release-Highlights-of-2025.pdf | Official |
| Covered employers pay **1% of wages** (≥10 Malaysian staff) | HRD Corp Employer Registration, https://hrdcorp.gov.my/employer/ (31 Oct) | Official |
| >100,000 registered employers, >4.8m registered workers | NST, Aug 2025, https://www.nst.com.my/news/nation/2025/08/1263966/hrd-corp-registers-over-48mil-employees-100000-employers-says-steven (31 Oct) | Secondary |
| Employees **12.63m** of 16.87m employed; unemployment 2.9% (Aug 2026) | DOSM Labour Force Statistics Aug 2026, 9 Oct 2026, https://www.dosm.gov.my/portal-main/release-content/labour-force-statistics-aug2026 | Official |
| Median monthly salary **RM2,940** (2025) | DOSM Salaries & Wages Survey 2025, 21 Sep 2026, https://www.dosm.gov.my/portal-main/release-content/salaries-and-wages-survey-report- | Official |
| Paid-report market sizes (e.g. Malaysia IT training USD 347.1m, 2025) have invisible methods; not used for TAM | IMARC, https://www.imarcgroup.com/malaysia-it-training-market | Paid report |

**Demand signals**

| Finding | Source | Class |
|---|---|---|
| **4.2m workers (28%)** highly exposed to generative AI, +2.5m medium-high; women, young, clerical and urban workers most exposed; exposure ≠ job loss | ISIS Malaysia & World Bank, Jul 2025, https://www.isis.org.my/2025/07/06/novel-ai-technologies-and-the-future-of-work-in-malaysia/ | Official research |
| **~620,000 jobs (18%)** in 10 sectors highly impacted by AI/digital/green within 3–5 years; GBS 32% | The Edge on TalentCorp study, Nov 2024, https://theedgemalaysia.com/node/734414 | Secondary |
| Graduate skill-related underemployment **32.2% (1.60m)**; **66.0%** for age ≤24 | DOSM Graduates Statistics 2024, 31 Oct 2025, https://www.dosm.gov.my/uploads/release-content/file_20260401145140.pdf | Official |
| MyCOL 2024/2025 lists **66** critical occupation groups (Adept stores Table 7; one reviewed role crosswalk) | TalentCorp; repo `docs/reference/critical-occupations.provenance.json` | Official, in repo |
| National AI Action Plan 2026–2030: up to **300,000** new AI roles by 2030 | NST, 22 Oct 2026, https://www.nst.com.my/amp/business/economy/2026/10/1561294/malaysia-targets-300000-ai-jobs-2030 | Secondary |
| PERKESO EIS: 117,733 job seekers re-employed Jan–14 Aug 2026; training via active labour-market programmes | Bernama, 18 Oct 2026, https://bernama.com/en/general/news.php?id=2621984 | Secondary |
| Malaysia attrition **18.2%** (2025); 2026 salary budgets +4.8% | Aon release, 11 Dec 2025, https://www.aon.com/apac/in-the-press/asia-newsroom/2025/aon-survey-projects-4-8-percent-salary-growth-for-malaysia-in-2026 | Secondary |

**Users (secondary evidence only; no team interviews recorded — [TODO: team adds any real discovery calls])**: P1 displaced clerical/GBS adult (ISIS, TalentCorp rows above); P2 fresh graduate (DOSM 66.0% ≤24 underemployment); P3 career switcher (Aon 18.2% attrition; PERKESO re-employment); P4 HR/L&D manager — **first buyer** (HRD Corp RM2.62bn spend); P5 TVET/university advisor — second buyer (1,996 TVET institutions, National TVET Portal 31 Oct; 65 private universities, 38 university colleges, 252 colleges, MIDA Feb 2026, https://www.mida.gov.my/industries/services/education-services/).

**Why HR would buy:** (1) spend levy-funded training on a named, sourced gap toward a named role; (2) plan toward courses flagged HRD-claimable (HRD Corp e-learning claims are hour-based, minimum 1 hour and one complete module: https://supportcentre.hrdcorp.gov.my/portal/en/kb/articles/e-learning-programme-financial-assistance); (3) internal mobility against 18.2% attrition; (4) consent-gated, no-protected-attribute ranking with no hiring/firing automation. **Adept's own subscription is not shown to be HRD-claimable**; vendor blogs say pre-approved LMS subscriptions from registered providers can be (https://disprz.ai/blog/hrdf-digital-learning-lms-malaysia) — test via training-provider registration or bundling.

**Pricing vs purchasing power and competitors**

| Product | Price signal | Adept difference |
|---|---|---|
| LinkedIn Learning Teams | US$379.88/licence/yr (https://www.linkedin.com/help/learning/answer/a768297) ≈ RM128/month at BNM USD selling 4.056, 30 Oct 2026 (https://api.bnm.gov.my/public/exchange-rate/USD) — estimate | Content library; Adept is the decision layer pointing to free/paid courses |
| Coursera for Teams | ~US$399/user/yr (third-party, https://trainingcost.com/coursera-for-business-pricing) | Same |
| Workday Skills Cloud | Quote-only, HCM bundle (https://www.gartner.com/reviews/product/workday-skills-cloud) | Enterprise; no public Malaysia-specific signals |
| BrioHR | RM3 training / RM7 talent per employee/month, RM200 minimum (31 Oct) | HRMS admin; Adept decides *which* gap/course, then exports |
| MyMahir / MyFutureJobs | Free public portals | Adept complements with person-level explained gap + consented team view |
| **Adept (test price)** | **RM6/active seat/month** (= 0.2% of median monthly salary; estimate), RM10 deeper tier | Grounded catalogue IDs, published formula, Malaysia data (MyCOL, DOSM, MY job feeds, MYR, HRD flag), two-sided consent |

**Moat to test:** grounded no-invention catalogue (15/15 automated synthetic journeys passed checks that every planned course/skill ID resolves to a sourced catalogue record — `docs/evidence/kpi-automated-journeys.md`, 30 Oct 2026, local fixture); explainable gap (0.45 skill + 0.25 trend + 0.30 interest, `src/api/app/features/matching/scoring.py`); Malaysia-specific data plumbing; individual + organisation two-sided model.

**TAM / SAM / SOM (estimates at RM72/seat/year):** TAM = 4.8m HRD-registered workers × RM72 ≈ **RM345.6m/yr** (cross-check: ISIS 4.2m exposed × RM72 ≈ RM302.4m). SAM = 620,000 highly impacted jobs × RM72 ≈ **RM44.6m/yr**. SOM year 5 (base) ≈ **RM3.5m/yr** = 30,000 seats (4.8% of SAM seats) + institution licences.

**3–5-year projection (estimate; every input is an assumption)** — employers × seats × price (RM6 in 2027, RM8 blended after) × 12 + institutions × flat licence (RM20k 2028–29, RM25k after). Costs: team at an assumed RM6,000/month loaded per FTE (2, 4, 6, 9, 12 FTE); infrastructure assumed US$117, 400, 1,000, 2,500, 5,000/month × 4.056; sales/partner cost 20% of revenue.

| Year | Employers × seats | Institutions | Revenue (RM) | Team + infra + sales (RM) | Operating result (RM) |
|---|---|---|---:|---:|---:|
| 2027 | 5 × 50 | 0 | 18,000 | 153,295 | −135,295 |
| 2028 | 20 × 60 | 3 | 175,200 | 342,509 | −167,309 |
| 2029 | 60 × 80 | 8 | 620,800 | 604,832 | 15,968 |
| 2030 | 150 × 100 | 15 | 1,815,000 | 1,132,680 | 682,320 |
| 2031 | 300 × 100 | 25 | 3,505,000 | 1,808,360 | 1,696,640 |

Low case (half the customers) reaches RM1.74m revenue in 2031; high case (1.5×) RM5.27m. Cumulative pre-break-even need in the base case ≈ **RM0.30m** (estimate). Year-5 base share = 300 of >100,000 registered employers (0.3%). **Why Adept can reach it:** deterministic reads mean no model cost per page view and one shared daily refresh for all customers, so marginal cost per seat is mostly support time; the catalogue and Malaysian sources are reused across every customer. Gates before spending: paid pilot → renewal → claimability answer → measured capacity.

**Not found:** an official Malaysian HR/L&D software market size; a 2026 national count of registered employers; any official statement that skills-planning SaaS is HRD-claimable; a Malaysia replacement-cost-per-employee benchmark.

### Evidence classifications and source register

**Measured** = source logs/invoice/reproducible benchmark; **verified external fact** = directly read authoritative publisher; **planning assumption** = hypothetical for decision testing; **derived** = arithmetic from labelled inputs; **unknown** = missing proof. A URL's live page can change: the retrieval date above is part of each claim. Price figures below are **listed rates, not team invoices**. No USD→MYR conversion is silently applied.

| Input / exact unit | Evidence class, publisher and limits |
|---|---|
| 1% levy on wages for covered employers with ≥10 Malaysian staff; 0.5% voluntary for 5–9 | **Verified external fact.** HRD Corp, Employer Registration guidance, undated, retrieved 31 Oct 2026. Does not mean subscriptions are claimable. |
| BrioHR Training RM3/month, Talent Essentials RM7/month, minimum RM200/month | **Verified external listed rate.** BrioHR, Malaysia Pricing Plans, undated, retrieved 31 Oct 2026. Rate is modular with billable-employee conditions; an individual quote may differ. |
| Swingvy Premium RM8.50/user/month, five-user minimum | **Verified external listed rate.** Swingvy Malaysia Pricing, undated, retrieved 31 Oct 2026; payroll and annual discount separate. |
| Kakitangan software | **Unknown price.** The vendor's estimator did not render a comparable rate when unconfigured on 31 Oct 2026; RM0 is not a published price. |
| 8.09m persons employed by MSMEs = 48.7% of Malaysian employment, 2025 | **Verified external fact.** DOSM, MSME Performance 2025, published 30 Jul 2026; persons are not buyers or seats. |
| 1,996 TVET institutions = 895 public + 52 state/statutory + 1,049 JPK private | **Verified external count.** National TVET Portal, undated counters retrieved 31 Oct 2026; alternate official population definitions exist and this is a separate buyer segment. |
| 100,000+ HRD Corp-registered employers | **Secondary reported fact.** NST reporting a ministerial reply, Aug 2025; no primary buyer roster verified; registered is not qualified to buy. |
| RM2.5bn collected / RM2.44bn grants disbursed FY2025 | **Secondary.** The Edge Malaysia report on HRD Corp financials; primary financial PDF not independently text-verified here. Training money is not SaaS revenue. |
| 56% AI use / 26% training in Malaysia (Phase 1 context) | **Historical secondary quote.** Preliminary submission attributes to Hays Asia Salary Guide 2025; the public landing page does not reproduce values. Verify survey table/sample before hero use. |
| 15/15 local scripted synthetic API journeys, per-persona medians 0.091–0.236s | **Measured in isolated local tests**, 30 Oct 2026, CSV/in-memory historical fixture; excludes human, browser, network and paid model. Not an achieved time-to-plan KPI. |
| 0 human attempts and null matched medians | **Recorded absence**, 30 Oct 2026; human trial protocol not run. |

**Market trend is not demand validation:** Malaysian training spend and employment scale establish a large context; interviews, purchase orders and renewals must establish *our* buyer demand. The TVET total overlaps some government-funded education ecosystems; never add education students to employer seats to inflate TAM. Older pitch notes claim “1.6M trainees (2025)” and “1% of SAM” without a defensible source/pipeline; **do not reuse**. Government portals MyFutureJobs and UpskillMalaysia are real alternatives. The latter explicitly includes skills and programme matching; do not claim Adept invented matching. Large enterprise products Coursera for Business and Degreed have broad course/skills offerings and custom pricing. Distinction to test: a *Malaysian employer's sourced, consent-aware training decision record*, not “better AI” or “cheaper than every competitor.”

### Customer value and pricing research, with honest counterweights

| Alternative | What it already does | Why test Adept as an add-on, not a replacement | Unresolved |
|---|---|---|---|
| BrioHR | Training paths, approvals, catalogue, attendance, course/provider evaluation on official page | Decide **which role/gap/source** warrants training, then export into existing admin workflow | RM3 module/RM7 talent bundle challenge RM15–25 legacy seat price; integrations absent |
| Swingvy | HR/payroll suite with public per-user MYR pricing | New input for role-gap justification, not duplicated HR administration | No direct procurement integration; five-user minimum elsewhere is not Adept demand |
| ChatGPT + spreadsheet | On-demand drafting at low friction | Validated IDs, source snapshots, conservative unmet gaps, employee consent and programme acceptance | Buyer may value human adviser more; must run blind reviewer task |
| HRD/e-LATiH / course sites | Courses and funding pathways | Decide priority across courses and keep dates/limitations visible | No blanket claim a software fee is HRD-claimable; verify with HRD Corp |
| TVET/placement portals | Cohort/career matching and public programmes | Potential later institution workflow | Public alternatives and procurement cycle make this a second market |

**Price hypotheses, not published Adept prices:** test RM6/active learner/month with 25–50-seat organisations and RM10 for a deeper manager/evidence tier. BrioHR Talent Essentials RM7 and All-in-One RM21 make the older RM15/RM25 plan difficult to justify for a thin add-on; neither RM6 nor RM10 is proven viable. Present paired written quotes to 10 eligible buyers; ask for a paid pilot/invoice rather than a survey-style “would you buy?” Retain refusals and procurement objections. No consumer LTV or referral commission is assumed.

## Part III — financial feasibility and scale model

### Cost/service inventory and evidence standard

| Cost object | How charged / primary source (USD unless noted) | Adept cash now, credit, future and labour classification |
|---|---|---|
| Replit Autoscale | Replit Aug 2026 cloud billing: $1/month base + $0.40 per **million requests** + $0.60 per **million compute units**; egress $0.05/GiB; rates effective 2026-08-01 for eligible billing cycles, retrieved 2026-10-31 | Actual product-attributable usage/invoice **unknown**. Sponsor Core subscription temporarily provided. Historic proof shows $6.38 **account** spend in its window, not current Adept-only cost |
| Replit managed PostgreSQL | Same official billing page: $0.16/**compute-hour**, $0.35/**GiB-month** DB storage. Outbound deployment egress is separate, not automatically DB egress | Actual compute-hours/storage, backup/restore cost, plan cap unknown; sponsor use not free after allowance |
| RunPod MiniLM Serverless | Serverless docs: running worker seconds billed, each period rounded **up to 1 second**; cold start + 5s default post-job idle billable, scaled-down time not billed. Public price table: L4/24GB group $0.75/GPU-hour, RTX4090/24GB $1.34/GPU-hour; actual deployed SKU unknown | Historical US$25 sponsor credit, balance and usage export unknown. Old 4090 Pod demo ≠ current MiniLM worker price/throughput |
| RunPod GLM-5.3 | Public hosted GLM endpoint is a **different billing product** from our MiniLM worker; exact endpoint invoice/rate and input/output tokens unknown | Configured Adi provider; default `LLM_PROVIDER=none`; never apply MiniLM GPU runtime rate to hosted GLM tokens |
| Gemini `gemini-embedding-001` | Google API pricing, undated page retrieved 2026-10-31: paid standard $0.15/**million input tokens**, batch $0.075; free tier conditions differ | Opt-in unfamiliar skill search/reindex; actual paid/free entitlement, requests and token count unknown |
| Gemini 3.5 Flash Lite fallback | Same Google page: paid standard $0.30/**million input tokens** + $2.50/**million output tokens**, plus applicable extras. 3.6 Flash and 3.1 Flash Lite backup prices/tier differ | Activated only on optional Adi failure; fallback/retry count unknown. Free allowance does not prove long-run zero |
| Feeds and rights | arXiv/UN/DOSM/board public endpoints have terms; keyed feeds and commercial data/enterprise integrations may require licence | Current licence/paid contracts **unknown**; do not count them as zero for production |
| Human service | Onboarding, mapping review, security/legal, privacy support, quality checks, sales; founder labour currently unpaid | Cash paid vs necessary sustainable staffing **unknown**; budget with `hours × loaded MYR hourly cost` |
| Development tools | Claude Code, Codex, Replit Agent, Greptile, Remotion/ElevenLabs etc. in declaration | Team subscriptions and presentation expenses **separate** from per-learner product inference; actual invoices unknown |

**Billing ledger needed before a commercial forecast:** Replit invoice by project/billing cycle (compute units, requests, DB compute-hours/GiB, backups, transfer), RunPod endpoint SKU/active workers/idletime/charged seconds and GLM endpoint token/rate report, Gemini usage by model/tier and paid flag, provider licences, staff time sheets and FX. Never expose credentials or private user records. A screenshot balance is a dated account observation, not cash cost allocated to Adept.

### Feature → billable event map (code path, not pricing guess)

| Trigger | Shared vs per-user, service event, cache and retry | Meter / measurement still required |
|---|---|---|
| PDF/DOCX/text CV parse and intake | Per-user local CPU/memory and DB writes; unknown phrase may request optional Gemini semantic suggestion; user confirms. No default paid LLM on upload | Parse CPU/p95, upload size, embeddings per CV, tokens/errors |
| Catalogue seed/re-index and explicit unfamiliar-skill search | Reindex changed labels once/shared when enabled; explicit phrase query per user optional Gemini; approved aliases resolve locally. No embedding on each dashboard view | Label count, tokens/label, cache hits, search rate, free/paid tier |
| Adi chat | Per signed-in request, optional RunPod GLM-5.3 then separately authenticated Gemini failover, finally deterministic guide. No model-generated entity/prose display | Input/output/thinking tokens and rates, fallback attempts, charged failed calls, latency |
| Trends ingestion + MiniLM | Shared daily due-check; bounded arXiv weeks, MiniLM per batch, then database publication; worker may cold-start. `TRENDS_MATCHER=auto` keeps MiniLM until equivalence gate | Paper/week and text length avg/p95, batches, billed seconds/attempt incl retries, successful publication |
| Stored trend rescore | Shared database/computation only, reuses paper inputs; no model call if cache complete | CPU and DB rows/time, recompute frequency |
| Jobs/course refresh | Shared daily or source cadence; documented public boards/providers, bounded requests, URLs; no LLM on normal sync | Request counts/status, per-source rules, fact age, licensed access, DB writes |
| Matches/pathway/radar/scenario/date filter | Per-user deterministic DB/reference reads and scores; date switch may change stored snapshot; **no inference on page view** | DB query counts, p50/p95, memory, pool concurrency, cache-hit ratio |
| Org aggregation | Per-org DB query over explicitly shared member records; no inference per card | Cohort size, suppression and query plans/CPU, cache invalidation |

**No double-charge:** a 30-day arXiv refresh is charged once per shared run, **not once per learner**. A failed job can still consume billable worker time or tokens. Some successful checks publish no new data; record changed-row counts. `LLM_PROVIDER=none` and `EMBEDDINGS_PROVIDER=none` are source defaults, not guaranteed deployed settings.

### Reproducible math — price, units and uncertainty

Let `x` be **MYR per USD at the actual payment date** (unknown; source later from BNM, record date/fees). Do **not** merge USD costs and MYR revenue without `x`. `ceil` applies **per billed worker period**, not to a whole month's summed seconds.

```
Replit_DB_USD = 0.16 USD/compute-hour × measured compute-hours
              + 0.35 USD/GiB-month × measured mean stored GiB-months
Replit_web_USD = 1 USD/month + 0.40 USD/(10^6 requests) × requests
               + 0.60 USD/(10^6 compute units) × compute units
               + 0.05 USD/GiB × outbound GiB
MiniLM_USD = Σ_billed-worker-periods [GPU_rate USD/hour × ceil(running_seconds)/3600 seconds/hour]
Gemini_embedding_USD = eligible_input_tokens / 10^6 × 0.15 USD (standard paid tier)
Gemini_fallback_USD = input_tokens/10^6 × 0.30 + output_tokens/10^6 × 2.50
Full_month_MYR = (Replit_web + Replit_DB + RunPod + Gemini + other USD costs) × x
               + MYR licensing + loaded human hours × MYR/hour + sales/support/admin
```

**Illustrative partial monthly computation, all unvalidated planning assumptions:** 720 DB compute-hours and 5 average GiB produce `720 h × $0.16/h + 5 GiB-month × $0.35/GiB-month = $115.20 + $1.75 = $116.95` for the DB **only**. Assume a MiniLM L4/24GB flex worker (actual SKU unknown), 30 daily jobs, two charged worker periods per job, 90 seconds each including cold start/idle: `30 × 2 × ceil(90s) = 5,400 worker-s = 1.5 h; 1.5 h × $0.75/h = $1.125`. A real run may invoke more batches or be skipped; this is **not** a measured cost. Assume 200 explicit embedding searches ×100 input tokens = 20,000 tokens → `$0.003` paid embedding price, if not free. Assume 300 Adi requests, 5% Gemini fallback with 2,000 input and 500 output tokens each: `15 × (2000×$0.30 + 500×$2.50)/1,000,000 = $0.02775`; the primary GLM charge and retries remain **unknown**, so do not call $0.02775 the chat cost. The Replit 1M compute-unit tariff needs actual compute units; 720 h does **not** imply any number of those units. Rounded bills and payment FX differ. These small model illustrations do not establish affordability once hosting, licensing and labour are counted.

### Pilot, 1k, 10k, 100k workload scenarios — **capacity not benchmarked**

Planning assumptions: each organisation pays for **50 seats**, 80% active in a month, one saved plan, two role checks, four trend-backed role reads (Radar trend-line charts are future work), 0.2 explicit embedding searches and 0.3 Adi chats per MAU/month; daily source cadence shared across all tenants (may skip if up-to-date). Typical Adi fallback tokens 2,000 input/500 output, p95 planning placeholder 8,000/1,500 to be **measured**; 5% fallback and retry load are **assumptions**, not observed rates. Daily peak concurrency, worker SKU, DB retention and storage bytes/record are unknown; model them as parameters `C_peak`, `B_worker`, `bytes_saved`. Assume 3 loaded service hours/org/month for onboarding amortisation + support + reviewer checks at **RM50/hour** solely to illustrate labour sensitivity (neither wage nor time is verified). At 2,500 organisations this staffing assumption alone is implausible for four founders.

| MAU scenario (assumed) | Organisations / paid seats | Plans, role checks, radar reads / month | Search, Adi chats / month | Shared source check/jobs | Price-hypothesis revenue @ RM6/paid seat/mo; human cost @3h/org×RM50/h |
|---|---:|---:|---:|---|---:|
| Pilot | 1 / 40; assume 32 MAU | 32 / 64 / 128 | 6.4 / 9.6 expected counts | <=30 due checks; actual workers only when due | RM240 revenue; RM150 service assumption |
| 1,000 | 25 / 1,250 | 1,000 / 2,000 / 4,000 | 200 / 300 | 30 shared daily checks, not 30,000 refreshes | RM7,500 revenue; RM3,750 service assumption |
| 10,000 | 250 / 12,500 | 10k / 20k / 40k | 2k / 3k | same shared cadence unless new source volume | RM75,000 revenue; RM37,500 service assumption |
| 100,000 | 2,500 / 125,000 | 100k / 200k / 400k | 20k / 30k | same cadence, heavier data and operational burden | RM750,000 revenue; RM375,000 service assumption |

These are **stress planning numbers, not market capture, platform throughput or a sales forecast**. Subscription billing unit is *paid seats*, not MAU; the table does not charge both included seats and an organisation licence. Retention of one plan/person/month adds `plans × bytes_saved` plus audit and source-history growth, not “free unlimited storage.” Peak/day ratio, burst concurrency and p95 payload are unknown. Measure DB p95 query/pool saturation, scheduler lock wait, worker seconds per batch and hosting compute units before proposing a Replit plan upgrade. A split worker/database host is justified only after consistent measured resource pressure and a tested migration/restore path. Content licences or human verification may dominate model bills.

### Pricing, margin, break-even, cash and downside

**Hypotheses**: RM6 per paid learner/month for a basic employer cohort; RM10 for a manager/verification tier only if independently validated. One 40-seat, 12-week pilot at RM6/month = `40×RM6×3=RM720` recognised over three months (**RM240/month**); an annual 40-seat booking at the same rate would be RM2,880, not the three-month pilot price. If a single invoice bills RM720 upfront, cash collected upon payment is RM720 but revenue is recognised RM240 per delivered month; if invoiced monthly and paid 30 days later, cash arrives later. No bookings, cash or revenue actually exist today.

Illustrative labour at 1 org ×3h/month×RM50/h = **RM150/month**, leaving **RM90/month before hosting, data rights, inference, billing fees, sales, taxes or fixed staffing**. If support increases to 5h/month, the same assumption costs RM250 and contribution is negative even before infrastructure. **Actual `v` variable delivery cost and `F` fixed monthly cost are unknown.** For a 40-seat RM6 tier: `contribution = RM240 − v`; if `v < RM240`, `break_even_orgs = ceil(F/(RM240−v))`, otherwise the price cannot break even. At RM10/seat for 40 seats revenue would be RM400/month but buyer willingness remains unknown. Any margin `=(revenue−delivery cost)/revenue` must include loaded onboarding/review labour and allocated cloud charges and cannot presently be stated. Do not call operating contribution profit; fixed team salaries, sales and founder compensation remain to be paid.

**Cash runway model:** opening cash + pilot invoices *actually collected by month* − Replit/RunPod/Gemini cash paid after credits expire − staffing/support/legal/sales cash − tax/working-capital changes. Record sponsor-credit expiry, 30–90 day procurement and payment lag, pilot onboarding spike, annual prepayment vs monthly recognition, renewal timing and delayed enterprise collections. No CAC, churn, LTV or payback metric exists without customers. Downside gates: only 1 of 10 interviews converts; LLM fallback/long context doubles charges; support rises from 3→5 h/org/mo; credit runs out; database compute-hours double; procurement takes 6 months; source licence becomes paid. Recompute with actual logs/invoices; do not hide a negative contribution behind free credits or founder time.

### Bottom-up Malaysian TAM / SAM / SOM — planning construct, not claimed revenue

**Verified denominator caveat:** DOSM's 1,069,831 MSME *establishments* (Economic Census 2023, release) are not unique employer contracts; 8.09m employed *persons* are not paid seats. Reported 100,000+ HRD-registered *employers* is **secondary**, and not all have an L&D buyer, eligible role family or procurement budget. We do not have a machine-readable qualified-employer count. Accordingly **verified numeric TAM, SAM and SOM do not yet exist.** Do not reuse legacy “3.5M×RM240” or a flat 1% capture claim.

```
TAM_MY_RM/year = N_eligible_employers × mean_purchasable_seats × price_RM/seat/month × 12
SAM_MY_RM/year = N_employers_with_budget+reachable_role+permitted_data+support_capacity × billable_seats × P × 12
SOM_3yr_RM/year = min(qualified_prospects×observed_win_rate,
                       procurement/onboarding/support capacity) × realised_seats × realised_P × 12
```

**Transparent illustration, not a measured market size:** if **1,000** organisations independently qualify through interviews/licensing (assumption), 40 seats each at RM6 (hypothesis) → `1,000×40×RM6×12 = RM2,880,000/year` **illustrative SAM**, *not* a verified opportunity. If a team can source **30** qualified prospects/year, wins **10%** (both untested) and supports **3** 40-seat accounts → `3×40×RM6×12=RM8,640/year` illustrative run-rate at year-end; procurement timing means actual first-year recognised revenue could be much less. TAM remains `N_eligible×seats×P×12` until a qualified buyer roster exists. Employer and TVET populations are separate sales motions; add neither seats nor contracts twice.

### Questions a CEO judge will ask — answer without bluffing

| Judge | Honest answer / evidence gate |
|---|---|
| Why pay when BrioHR Training is RM3? | We are testing a *pre-purchase role/gap decision* layer; administration is already served. If buyer time and course choices do not improve in a paid pilot, there is no purchase case. |
| Is RM6 profitable? | Unknown. RM240/month on a 40-seat pilot, assumed RM150 service leaves RM90 before every platform/marketing cost. We need real support logs and invoices. |
| Does HRD levy pay your subscription? | No verified permission. We will ask HRD Corp and use ordinary L&D software budget unless explicit written eligibility exists. |
| Does your AI predict which jobs vanish? | No calibrated Malaysian employment predictor. It compares sourced proxy trends and scenario assumptions; employers still make choices. |
| Can it handle 100k users on Replit? | Not benchmarked. Shared refresh reduces repeated inference but DB concurrency, paid service and support capacity must be load-tested; no provider migration promised. |
| What did you achieve against Phase 1 targets? | Code paths and 15 scripted synthetic journeys work locally, but no human timed test or independent 100% ID validity audit has yet proven targets. |
| What is the moat? | Hypothesis: local workflow, source/date integrity, consent and auditable decisions. Data/IP permissions and buyer adoption must be earned; a matching formula alone is not defensible. |

## Part IV — final presentation storyboard (≤15 slides)

**Deck is business-first, maximum 15 slides. This plan specifies 14; the product PRD above carries technical detail that the CEO audience should not read on screen.** Format 16:9, one thesis per slide, 1–3 graphic objects and ≤25–30 body words, source/date in a quiet footer (never omitted for a number). Suggested typography: title ~40–48pt, hero number ~88–120pt, body ≥22pt, source ≥12pt. Use Adept's deep green/sage/ink, one accent per slide; visual identity remains consistent with the app. No clipped source captions, word clouds, axis tricks, dual axes or decorative pies. Charts encode **one unit per axis**, display denominators, and use labels/patterns in addition to color. Do not make up a trend line from one observation. Images/screenshots must be captured from the verified build with synthetic data, and labelled as such. Speaker notes below contain the detail removed from screen.

| # · time | Slide thesis (on-screen copy) | Layout / visual, exact data and spoken narrative | Evidence gate |
|---|---|---|---|
| 1 · :15 | **Adept. Better training decisions for changing work.** | Dark cover; single worker → role → plan path; speaker introduces employer L&D buyer and member autonomy | No numeric claim |
| 2 · :30 | **Training need is growing. The choice is hard.** | Large **8.09m** with small caption “persons employed by Malaysian MSMEs, 2025”, and **48.7%** share; two clean labelled horizontal marks, not a fake time series. Explain this is the *context*, not Adept users (DOSM, 2026-07-30) | Consider one better verified buyer-pain figure only after source methodology checked; never imply 8.09m are reskilling buyers |
| 3 · :25 | **The manager buys a course before proving the gap.** | One-screen manual workflow with three fragmented cards: role list / spreadsheet / course catalogue; one red connector labelled “decision not traceable”. Speaker asks who is trained, for which role, why this course | Interview needed to validate frequency; mark workflow as hypothesis |
| 4 · :25 | **Adept starts with the gap.** | 4-stage pipeline: confirmed skills → dated signal → explained role/gap → ordered, costed training plan; emphasis on human approval, small source label | Trace through source and synthetic demo |
| 5 · :35 | **A learner sees an actionable next step.** | Three actual synthetic UI crops (confirmed skills, score/gap, course plan) with 1-line annotations; large valid-ID target “100%*” only if visibly marked **Phase 1 target, unverified** | Screenshot revision/snapshot; avoid claiming achieved speed-up |
| 6 · :30 | **HR sees gaps, members control sharing.** | Split-screen consent toggle + aggregate heatmap/programme approval; 3 terse bullets: invite, review, fund. Narrate no autonomous HR decision | Server-side role/consent checks, synthetic org |
| 7 · :30 | **Estimates, not employment promises.** | Show one role card with its Moderate/Fast trend component and source/snapshot badge; no vacancy axis. Radar trend-line charts are listed as future work | Actual final API response and production source dates; no 2024 replay as current |
| 8 · :25 | **The training wallet exists; our fee is not yet funded.** | Hero **1%** levy for covered ≥10-employee employers; slim qualifier “wages, not SaaS claimability” (HRD Corp); beside it show buyer → member → provider, no bogus cash flow | HRD Corp eligibility and software funding unresolved |
| 9 · :30 | **Why add Adept to the existing stack?** | Four-column comparison of manager spreadsheet, generic chat, HRMS training admin, Adept hypothesis; only check features confirmed from vendor pages; call out BrioHR RM3 training/RM7 bundle footer | Buyer interview and blind plan-review needed; no blanket competitor weakness |
| 10 · :30 | **Start with one Malaysian operations team.** | Concentric *funnel* of **qualified employer → paid pilot → renewal**, counts remain `?` until recruited; TVET next, not simultaneous. Use 100,000+ registered employers only with “secondary, not eligible buyers” footnote, preferably omit | 10 discovery interviews + qualified list |
| 11 · :35 | **A paid pilot is the proof, not downloads.** | Side-by-side manual vs Adept task, 8–12 weeks, 25–50 seats. Three small gates: valid plan, decision minutes, paid renewal. Add **0 human trials** as current status, not a failure hidden | Pre-register, independent reviewer, anonymised results |
| 12 · :30 | **RM6 is a price test, not revenue.** | One large equation `40 paid seats × RM6/month × 3 months = RM720`; below: “RM150/month human service *assumption*; cloud bill unknown.” Compare RM7 incumbent bundle without implying equal feature scope | Actual competitor page, assumptions labelled; correct 3-month vs annual math |
| 13 · :25 | **Replit first. Upgrade when measured.** | Simple shared refresh → managed PG → cached reads; small markers “p95 query / worker seconds / support hours”; no AWS boxes or capacity claim | Run records, DB usage, restore test missing |
| 14 · :20 | **Prove the decision, earn the renewal.** | 3-step roadmap: verify live source → paid buyer pilot → scoped integration; closing CTA “one team, one role family, one measured decision.” | No projected profit/TAM without qualified buyers |

**Five mandatory themes covered:** problem 2–3; solution/impact 4/7/11; product 5–6; market/differentiation 8–10; business/funding/next investment 12–14. User target appears in 1, 6, 10. Leave screenshots as placeholders until captured from a verified production-like revision. Investor numbers should come from measured customer time or primary statistics, not invented “Adept reduces X%” forecasts. Use the real Phase 1 targets in report, not the pilot's proposed 20% reduction. Pitch in 5–7 minutes, reserve Q&A for the technical appendix/PRD. If a flattened PDF is required, export the completed deck and verify it independently; this file is a deck **plan**, not the deck itself.

## Part V — delivery gates and team questions

| When | Work, effort and dependency | Acceptance evidence |
|---|---|---|
| Before judging | Verify deployed SHA, 6-step synthetic journey, real changed-source publication (1–2 team days after ops setup); reconcile private report/tool fields and source licences (1–2 days) | Run URL/status, snapshot/observation/retrieval dates, screenshots, PDF word-limit check and leader approval |
| Next 30 days | 10 buyer interviews and blind manual-vs-Adept task design (1–2 weeks); bill instrumentation and disposable restore drill (3–7 days) | Interview notes with refusals, cost ledger/invoices, independent plan rubric, restored test fixture |
| Following 90 days | One 25–50 learner paid pilot under appropriate consent and contract, then integration request only from buyer (8–12 weeks) | Signed payment and terms, reviewed results/failures, renewal/stop decision and legal review |

**Stop expanding:** unsupported “predict exact job losses”, static research called live, SDG-badge-as-impact, arbitrary new role categories, certificate equivalence, automatic hiring decisions, invented ROI/market capture, per-page LLM calls. None of these makes a buyer's actual decision easier.

**Questions only the team can settle:** What are the official 48-hour event timestamps and final deployed SHA/snapshot? Which actual team tools/media/licences and employer IP agreements need disclosure? Can a prospective employer pay for a three-month pilot from its own software budget, and which decision would the manager replace? Who will own 8–12 weeks of buyer support, independent plan review and compliance work? How much cash (not credits) is available to keep Replit/RunPod running after judging?
