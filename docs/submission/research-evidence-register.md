# Adept Finalist Evidence Register

**Internal working register, not one of the three organiser-ready documents.** This file holds the source URLs and repository path pointers deliberately omitted from the copy-ready report, declaration and pitch PRD. All external retrievals below occurred 2026-10-31 unless noted. The working source revision reviewed is `origin/main` `0a7868c` (2026-10-31 23:29 MYT). No production/paid provider call or private data was accessed. A newer merge requires comparison before copying any claim into slides or PDFs.

## Evidence grades

- **Measured locally:** reproducible isolated synthetic harness/committed sample; not production/customer outcome.
- **Verified external:** authoritative publisher page was fetched and its unit/conditions captured.
- **Secondary:** report relays original source but original value/definition was not fully checked.
- **Assumed:** scenario input for a falsifiable price/workload test; not observed usage/revenue.
- **Derived:** arithmetic from inputs labelled by the grades above.
- **Unknown:** neither vendor billing nor live deployment/customer evidence available.

## Competition, phase boundary and implementation

| Claim | Evidence / exact location | Limit |
|---|---|---|
| Final report/declaration organiser fields and 250/300/250, 200/100/100/150/150 word limits | Supplied user-transcribed finalist organiser templates dated 2026-10-31; downloaded guide PDF pages 11–12 for rubric | Template is not an authorisation to sign declarations. |
| Official baseline *before 2026-10-25 08:00 MYT* | `git rev-list -1 --before='2026-10-25T08:00:00+08:00' origin/main` → `b34c06c2c94052debea078c8fe6cbec2d3479747` at 07:46:32 MYT | Comparison point is not necessarily the 48-hour physical sprint start. |
| Preliminary KPI, actual | `submission/SDC2026_Pecel-Lele_Preliminary.pdf` page 10: historical Hays 56%/26% *problem context*; proposed 100% catalogue-ID validity and median <3 minutes across five synthetic personas | Phase 1 did **not** set a 20% manual-time reduction. No Phase 1 timed baseline. |
| End-of-24-Oct `2a802c6` vs 08:00 cutoff difference | `git diff 2a802c6..b34c06c` has 31 files, incl. signed-account guardrail edits, five synthetic CVs and sponsor PDFs | Do not call the 08:00 state a bare skeleton. |
| Final change scope at `0a7868c` | `git diff --name-status b34c06c..0a7868c`: new data-refresh and impact features, trend comparison, source/paper store, improvements to profile, matching, path, SDG, org, UI | File existence and tests do not prove deployed/recent. |
| Actual seeded catalogue sizes | CSV `src/data/seed/taxonomy/skills.csv` = 142 rows; `roles.csv` = 48 rows, 33 `is_target=true`; `src/data/seed/courses/courses.csv` = 104; `src/data/seed/jobs/job_postings.csv` = 1,175; `src/data/seed/sdg/role_sdg_map.csv` = 88 and `skill_sdg_map.csv` = 167 | These are source rows at pinned revision, not prod database contents. Historical 110/140/98 counts refer to older captures. |
| Stored impact and local timing | `docs/evidence/impact-evidence.md` says 2026-10-20 fixture, research observations 2024-10-13–19; `docs/evidence/kpi-automated-journeys.md` 15/15 scripted local journeys, 0.091–0.236 seconds per-persona median; `docs/evidence/kpi-human-summary.json` 0 attempted trials | Historical fixture is not a current AI feed; automated timing excludes human/browser/network. |
| Scoring and guarded entities | `src/api/app/features/matching/scoring.py` 0.45/0.25/0.30; `src/api/app/features/pathway/engine.py` course ordering; `src/api/app/core/llm/gateway.py` ID validation; `src/data/seed/sdg/provenance.json` team-alignment caveat | Deterministic score is not a validated employment forecast; badge is not outcome. |
| App-side refresh | `docs/data-refresh.md`; `.github/workflows/automatic-data-refresh.yml`; `src/api/app/features/data_refresh/{router,service,repository,automatic_trends}.py`; `src/api/app/features/trends/comparison.py` | Owner must migrate/provision/deploy, verify fresh snapshot and scheduled run. GitHub runner's private Replit DB hostname is unreachable from external CI. |
| Snapshot versus range behaviour | `src/web/src/features/trends/components/RadarView.tsx`, `TrendRangeCard.tsx`, `src/api/app/features/trends/comparison.py`, PR #110 | Snapshot picker changes radar data edition; chart range selects research-share comparison only, not every recommendation. Role/category share is derived from skills. |
| Proof-of-use boundaries | `submission/SDC2026_Pecel Lele_Replit_POU.pdf` screenshots include a dated US$6.38 **account** spend and Asia Autoscale screenshot. `submission/SDC2026_Pecel Lele_Runpod_POU.pdf` shows 110 embeddings in 0.354s on an RTX 4090 Pod and later MiniLM Serverless endpoint | Old account balance/Pod time/region screenshots are not present bill, real refresh proof, or per-user model cost. Do not edit historical screenshots. |

## Malaysian demand, buyer and competitor sources

| ID | Publisher / exact population or product / date | URL and classification | Caution |
|---|---|---|---|
| M1 | DOSM *MSME Performance 2025*, released 2026-07-30: 8.09m persons = 48.7% total Malaysian employment | https://www.dosm.gov.my/portal-main/release-content/micro-small--medium-enterprises-msmes-performance-2025 · verified external | Employed persons, not distinct employers or paid learner seats. |
| M2 | DOSM *Economic Census 2023: SMEs*, released 2024-09-19: 1,069,831 MSME **establishments** | https://www.dosm.gov.my/portal-main/release-content/economic-census-2023-profile-of-small-and-medium-enterprises · verified external | Establishments ≠ unique companies; may not be HRD buyers. |
| M3 | HRD Corp *Employer Registration*, undated, retrieved 2026-10-31: levy 1% wages for covered employers with ≥10 Malaysian workers, voluntary 0.5% for 5–9 | https://hrdcorp.gov.my/employer/ · verified external | HRD levy is not proven usable for SaaS subscription payments. |
| M4 | National TVET Portal counters, retrieved 2026-10-31: 895 public + 52 state/statutory + 1,049 JPK private = 1,996 institutions | https://www.tvet.gov.my/ · verified external, site does not date counters | Other official cuts report 685 or 1,368 with different definitions; no additivity with employers. |
| M5 | Ministry of Higher Education public-university list: 20 public universities, checked 2026-10-31 | https://biasiswa.mohe.gov.my/biasiswa-mybsa/ · source pointer only; agent did not confirm direct current document path | Not added to TVET total due overlap and definition issues. Private HEI count unknown. |
| M6 | Ministerial report (NST), 2025-08: >100k HRD Corp-registered employers, >4.8m registered workers | https://www.nst.com.my/news/nation/2025/08/1263966/hrd-corp-registers-over-48mil-employees-100000-employers-says-steven · secondary | Registered ≠ active/eligible/paid. Primary count/list unavailable in research. |
| M7 | HRD Corp FY2025 financial statement relayed in The Edge: RM2.5bn levy collected, RM2.44bn grants disbursed | https://theedgemalaysia.com/node/809678 ; source statement https://hrdcorp.gov.my/wp-content/uploads/2026/07/HRD-Corp-Financial-Report-2025-Digital-Version.pdf · secondary because primary PDF text could not be verified here | Grants ≠ SaaS wallet, no budget allocated to Adept; do not call 2.86m *training places* 1.6m distinct trainees. |
| M8 | Hays Asia Salary Guide 2025 Malaysian 56% AI use / 26% trained, cited in Phase 1 PDF | https://www.hays.com.my/hays-asia-salary-guide-2025 · **unverified against primary value** | Obtain original survey table/sample; do not use as sourced hero figure now. |
| M9 | BrioHR Malaysia Pricing Plans, undated retrieved 2026-10-31: Training RM3, Talent Essentials RM7, Talent Pro RM9, minimum RM200/month | https://briohr.com/pricing-plans-my/ · verified external | Prices per billable employees per month subject to modular minimum; feature page describes training paths/catalogue/attendance, not proven no forecasting. |
| M10 | Swingvy Malaysian pricing, undated retrieved 2026-10-31: Premium RM8.50/user/month; minimum five users | https://www.swingvy.com/my/pricing ; https://help.swingvy.com/knowledge/swingvy-billing-overview · verified external | SG dollar prices are a different country; payroll module extra. |
| M11 | Kakitangan pricing, fetched 2026-10-31: public estimator does not render comparable configured price | https://www.kakitangan.com/pricing · verified access, **unknown rate** | Estimator's RM0 empty state is not the vendor's price. |
| M12 | Coursera for Business, Degreed pricing pages, fetched 2026-10-31 | https://www.coursera.org/business/compare-plans ; https://degreed.com/experience/pricing/ · primary product-tier facts, prices not rendered/custom | Do not quote secondary USD/AUD Coursera per-seat figures as Malaysian vendor quote. |
| M13 | HRD Corp training provider/HCC scheme, retrieved 2026-10-31 | https://supportcentre.hrdcorp.gov.my/portal/en/kb/articles/training-provider-registration ; https://hrdcorp.gov.my/hrdcorp-claimable-courses · verified external | Software subscription claimability unverified; provider registration has additional company/office requirements. |
| M14 | Malaysian public alternatives: HRD UpskillMalaysia and MyFutureJobs | https://upskillmalaysia.gov.my/aboutusp ; https://myfuturejobs.gov.my/ · verified official existence | Already offer programme/job matching; do not claim no alternatives. |

## Provider and cost source ledger

| ID | Source / exact product and units | Date / terms / URL | Evidence status |
|---|---|---|---|
| C1 | Replit cloud billing update: PostgreSQL $0.16/compute-hour + $0.35/GiB-month; Autoscale $1/month + $0.40/1m requests + $0.60/1m compute units; deployment outbound $0.05/GiB | Effective for each eligible account's first cycle on/after 2026-08-01, retrieved 2026-10-31. https://docs.replit.com/billing/aug-cloud-billing-updates | Verified *public tariff* in USD, not Adept invoice. DB egress rate not separately specified; region/account plan and use unknown. |
| C2 | RunPod Serverless public GPU-rate table: 24GB L4/A5000/3090/MIG group $0.75/GPU-hour; RTX4090/24GB $1.34/GPU-hour | Undated live table retrieved 2026-10-31. https://www.runpod.io/pricing | Verified public USD list rate; MiniLM actual SKU/region/worker count not recorded. Old Pod demo does not determine Serverless SKU. |
| C3 | RunPod Flex Serverless worker billing: running seconds, ceil to next second **per billed period**; cold-start running time and default 5s post-job idle billed; scaled-down not billed; Active worker billed 24/7 | Retrieved 2026-10-31. https://docs.runpod.io/serverless/pricing | Verified official billing mechanics. Do not round aggregate month as one job. GLM hosted endpoint pricing must be obtained separately. |
| C4 | Google `gemini-embedding-001` paid standard $0.15/1m input tokens; batch $0.075. Gemini 3.5 Flash Lite paid standard $0.30/1m input + $2.50/1m output (thinking output included) | Pricing page undated, retrieved 2026-10-31. https://ai.google.dev/gemini-api/docs/pricing | Verified public USD paid tiers, not Adept's actual tier; free allowances/batch eligibility and Gemini backup model rates differ. |
| C5 | FX: actual MYR/USD settlement rate, sponsor expiration, Replit/RunPod/Gemini bills, staff loaded rate | No bill or FX settlement document provided. BNM reference API https://api.bnm.gov.my/ | Unknown; do not convert USD cost to MYR with a guessed current rate or call credits profit. |

## Financial scenario input audit

| Input | Classification | Change test |
|---|---|---|
| RM6/basic and RM10/deeper employer seat-month, 40-seat 3-month paid pilot | Planning price hypothesis, not contract/revenue | Written quotes to 10 buyer decision-makers + signed paid invoice; 40×6×3=RM720, not RM2,880 (the latter is annual). |
| 50 billed seats/org, 80% MAU, one plan + two role checks + four radar reads, 0.2 skill searches + 0.3 chats/MAU/month | Pure workload assumptions, not user telemetry | Instrument consented counters, p95 requests, paid provider usage. |
| 3 support/verification hours per org-month at RM50 loaded MYR/hour | Pure labour assumptions, not wage/invoice | Time sheets, fully loaded salary/tax/overhead, onboarding separate; pilot 3×50=RM150/month. |
| L4 at $0.75/h × 30 days ×2 periods/day ×90 billed seconds/period | Conditional illustration; SKU and runtime unknown | 5,400 s/3,600 = 1.5 h ×$0.75/h = $1.125 *if* actually charged; RunPod billing export. |
| 720 DB compute-hours +5 mean stored GiB-month | Conditional illustration, not measured | 720×$0.16 +5×$0.35 = $116.95, excludes Autoscale and backup, actual compute mode/plan may differ. |
| SAM example 1,000 qualified orgs×40 seats×RM6×12=RM2.88m/yr, SOM example 3 accounts×40×RM6×12=RM8,640/yr | Derived from wholly hypothetical eligibility, conversion and pricing | Qualify a buyer roster, track pipeline→procurement→invoice→renewal and support capacity. No numeric TAM claim. |

## Publication and freshness actions not performed

Do not start production refresh, seed/migrate live databases, buy resources or expose credentials to fill evidence gaps. Owner must identify deployed build, verify `data/freshness` against measured weeks and schema, inspect real per-source success IDs, confirm licences and complete private disclosures. Repository check/test success is local source verification, not a live outcome.
