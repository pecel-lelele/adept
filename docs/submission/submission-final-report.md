SDC HACKATHON 2026

Phase 2: Final Project & Prototype Report

Hosted by Xiamen University Malaysia (XMUM) AI Club

Submission Deadline: 1 November 2026

Instructions: Complete every field below and submit as a single PDF document named “SDC2026_TeamName_Final.pdf” together with your pitch deck and a working deployment link. Answers must comply with the word limits stated for each open-ended question. Section 3 requires concrete, verifiable evidence. Unsupported claims will not be credited by judges.

## Team & Project Overview

Team Name

> Pecel Lele

Project / Product Name

> Adept

Final Live Deployment URL

> [https://adept-my.replit.app](https://adept-my.replit.app)

Codebase Repository URL

> [https://github.com/pecel-lelele/adept](https://github.com/pecel-lelele/adept)

Name (Leader)

> David Kurniawan

Email & phone (Leader)

> [To be completed in the signed version]

## Project Description

[Maximum 250 words]

<!-- answer:start final-description limit=250 -->
> Adept is a career and workforce reskilling platform for Malaysia. It helps working adults, graduates and career switchers decide which skills to build next, and it helps HR teams and career centres see where their people need support.

> A user uploads a sample CV or answers a short questionnaire, then confirms each skill. Adept shows rising and declining skills from dated research and labour signals, ranks future roles with an explainable score and a skills gap, and builds an ordered learning plan from real courses within the user's time and budget. Each role and skill links to UN Sustainable Development Goal targets with a stated reason. Two AI-pace scenarios show how recommendations shift, and every forecast is labelled as an estimate with its source and date.

> Organisation managers invite members with a join code, view a consent-based team skills-gap heatmap and send costed programmes that each member chooses to accept. Personal plans stay private.

> The assistant, Adi, selects validated answers written by the application, so it cannot invent jobs, courses or statistics. Deterministic rules produce the matches and plans. Adept supports human judgement and never makes hiring, firing, promotion or admission decisions.

> The product runs in English, Bahasa Melayu and Chinese. It addresses SDG 4 targets 4.3 and 4.4, and SDG 8 targets 8.2 and 8.5.
<!-- answer:end final-description -->

## Upgraded Product & Technical Execution

[[break]]

### 3.1 Final System Architecture

Provide a detailed description (and, if possible, an attached technical diagram) of your fully built system. Explain how your application integrates GenAI APIs, database structures, and backend/frontend frameworks into one unified solution.

> One backend serves both the individual and the organisation workspace. A Python supervisor on Replit Autoscale starts a public Next.js 16 server and a private FastAPI service, and it checks that both are ready. Next.js renders the interface in three languages and forwards API requests to FastAPI over a signed internal boundary. OpenAPI contracts generate the TypeScript client, so both sides share one schema.

> **Database.** Replit PostgreSQL holds accounts, profiles, confirmed skills, memberships, plans, progress, evidence and the catalogue of skills, roles, courses and certifications. Dated trend snapshots, job postings and SDG mappings sit beside them. Migrations are append-only timestamped SQL files. Vector tables store skill and catalogue embeddings.

> **GenAI.** AI is used in three bounded places. The all-MiniLM-L6-v2 encoder on RunPod Serverless matches research papers to skills in a background batch job. Gemini Embedding 001 can suggest the nearest catalogue skill for an unknown CV phrase, and the person approves it. GLM-5.3 on RunPod, with Gemini failover, selects answer-block IDs for Adi; the server checks each ID and displays only its own wording. If a provider fails, a deterministic guide answers.

> **Recommendations.** Matching, gap analysis, course ordering and SDG contribution are deterministic Python functions over stored records, so a page view never waits for a model. Each recommendation carries its sources, snapshot date, scenario and estimate label.

> **Data refresh.** A daily GitHub Actions workflow asks the deployed app to refresh arXiv signals, Malaysian job postings, course checks and DOSM labour context. A failed source keeps the last valid snapshot and discloses it.

[[break]]

[[diagram]]

### 3.2 Implementation & Hackathon Deliverables

Describe what was successfully built, integrated, and deployed during the 48-hour physical sprint. Highlight any specific problem-solving steps your team took to pivot or improve the project from the Phase 1 preliminary design.

[Maximum 300 words]

<!-- answer:start final-implementation limit=300 -->
> The official sprint times were not published to the team, so this section covers work after the Phase 1 cutoff of 25 October 2026, 08:00 MYT. The public history records 196 non-merge commits since then, and they completed the six-stage journey.

> **Trend data.** The team built an administrator refresh control, a daily refresh workflow and a shared last-good fallback that labels stale data. RunPod cold starts were timing out, so MiniLM jobs now run asynchronously. A scheduled job could not reach Replit's private development database, so the deployed app now performs the refresh itself.

> **Matching and plans.** Scenario outlooks now share one robust trend scale, and interest can only add to a score. Onboarding settings visibly change the plan, and role titles are grounded in stored catalogue records. The catalogue grew to 142 skills, 33 target roles and 104 courses, including five in Bahasa Melayu.

> **Malaysian relevance.** Job surfaces now prioritise Malaysian employers and label old postings. TalentCorp's MyCOL list was added as a dated, non-ranking reference.

> **Organisations.** Members can propose a different role, sharing is optional, and heatmaps hide groups below three consenting members.

> **Trust.** The team added session revocation, a verified proxy boundary, a public privacy notice, a public impact page and fixed answers for Adi that always link to the right page. The CV step now records only skills the CV states and asks the person to confirm them.

> **Simplification.** On 1 November the team removed cluttered score arithmetic and the radar's trend-chart cards, which failed where migration data was missing. Cards now give plain reasons, what would raise the score and a compact Sources link.

> Browser journeys for desktop and mobile, source-attribution checks and generated contract checks guard this work. The prototype is published on Replit Autoscale at the link in Section 1.
<!-- answer:end final-implementation -->

## 4. Environmental & SDG Impact Verification

Validate the real-world impact of your built solution. Show concrete data that validate your environmental or social value proposition, compared against the baseline and KPI defined in previous phase submission.

The data and evidence you provide in this section will be used to assess SDG Impact, Technical Execution and Innovation scores. Vague claims or missing verification will weaken your score across all three categories.

Metric Category

Your Response

**Target SDG Metric Achievement**

Direct comparison between your Phase 1 baseline and your Phase 2 finalized prototype numbers

e.g., “Achieved a 24.5% reduction in computational execution overhead against the 20% initial target.”

> **Phase 1 baseline.** 56% of Malaysian professionals used AI at work and 26% had received training (Hays Malaysia, 2025). Phase 1 set two targets across five synthetic profiles: 100% catalogue-ID validity and a median time-to-plan below three minutes.

> **Catalogue-ID validity: target met.** Achieved 100%: all 46 recommended course IDs across five profiles and two scenarios resolve to catalogue records, against the 100% target.

> **Time-to-plan: partly measured.** The automated API journey from CV to saved plan completed 15 of 15 runs, with a median of 0.084 seconds. This excludes reading, skill confirmation, the browser and the network. The human stopwatch trials have not been run, so the three-minute target is not yet claimed as met.

> **SDG 4.3, learning cost.** 92 of 104 courses are free (88%). The median plan across the five profiles is 9.9 hours and 100% free. Plans cover SDG targets through a stated reason on every link: 26 targets and 88 role links.

> **SDG 8.5 and 10.3, fairness.** Across 75 name and background swaps, the largest change in any role's rank was zero.

**Verification Evidence Method**

How was this data verified?

e.g., codebase algorithmic profiling logs, hardware power-meter simulation readings, or database transaction counters.

> Each figure comes from a repeatable script that calls the production services and writes a dated result file:

> • Catalogue-ID validity: every course ID in each generated plan is checked against the course catalogue.

> • Learning cost, coverage and fairness: the production impact service recomputes these from the catalogue, and re-ranks each profile under name and background swaps.

> • API timing: an isolated run of 15 journeys records the time and status of every step.

> • Human planning time: a paired-trial protocol and calculator are ready, with no trials recorded yet.

> All runs use synthetic personas, with paid models switched off. They verify system behaviour on those profiles; they do not measure employment outcomes.

**Socio-Economic / Civic Value**

How does your deployed application translate into a scalable, real-world solution capable of being supported by civic or corporate partners?

> **Reach.** Adept starts with HR and L&D teams in global business services, a sector of about 120,000 Malaysian jobs (AGOS via Bernama, 2025), and with polytechnic career centres. The first planned step is one 50-seat employer pilot. TalentCorp reports 620,000 highly impacted jobs across 10 sectors employing 3.5 million people, which is the wider group.

> **Value.** Employers paid RM2.53 billion in HRD Corp levy in 2025 (HRD Corp Financial Report 2025). Adept shows where that training spend should go, while individuals use the product free. Employers or campuses fund the free tier, so people with less money still get a plan that respects their budget.

> **Privacy under PDPA.** CVs are read in memory and not stored. Members choose what HR sees, and small groups stay hidden. Users can export and delete their accounts.

> **Fairness.** Age, gender and background are not inputs to the score, and automated tests guard this. Three languages and a mobile layout widen access.

**Deployment & Commercial Feasibility**

e.g., modeled as an API service plugin designed for easy integration into existing corporate or institutional systems.

> **Model.** Adept is a per-seat subscription service: free for individuals, a proposed RM15 to RM25 per seat a month for organisations, and a campus licence. Prices are hypotheses that the pilot will test. HR-system integration is planned, not built.

> **Data freshness.** Workflows are scheduled to refresh data daily and audit sources weekly, and each recommendation links to its sources and date. The first scheduled publication on the live site still needs confirming.

> **Cost per month (estimates).** Our model gives about RM304 at 50 seats, RM1,973 at 2,000 seats and RM3,634 at 5,500 seats with 27,500 free users. That is about RM0.66 per paid seat at scale. It uses list prices checked on 1 November 2026: Replit Autoscale at US$2 base, US$0.60 per million compute units and US$0.40 per million requests; Replit database at US$0.16 per compute hour and US$0.35 per GiB; RunPod 16 GB flex at US$0.58 an hour; GLM-5.3 at US$0.77 and US$2.42 per million tokens; and Gemini embeddings at US$0.15 per million tokens, at RM4.0925 to the US dollar. Usage is assumed, because no production billing data exists yet.

### 4.1 Mathematical Proof / Code Logic Snippet (Optional, but holds bonus marks)

Paste the specific code section, mathematical formula, simulation log output, or calculation logic that proves the impact claims made above.

This proof is graded across three categories at once: Impact and Feasibility (does the math support your claim), Technical Execution (does it reflect what you actually built), as well as Innovation and Creativity (is the approach original).] Do not leave this section generic or copied from Phase 1.

> **Catalogue-ID validity.** validity = 100 × valid course IDs ÷ recommended course IDs = 100 × 46 ÷ 46 = 100%. Output of the validity script on the final code:

```
persona        scenario  courses  valid
demo-imran     both      1 x 2    2
demo-sofia     both      4 x 2    8
demo-meera     both      7 x 2    14
demo-adrian    both      3 x 2    6
demo-nur-hana  both      8 x 2    16
46/46 valid = 100.0%
```

> **Explainable score.** This is the production scoring function, with weights of 0.45 for skills, 0.25 for trend and 0.30 for interest. The profile type has no field for age, gender or background, so those values cannot reach the score, which supports the 75-swap result above.

```
def score_role(profile, role, scores, w):
    s = skill_overlap(profile, role)
    t, coverage = role_trend(role, scores)
    i = interest_fit(profile, role)
    i_contrib = NEUTRAL if i is None else i
    return _RoleScore(
        role_id=role.role_id,
        score=w.skill * s + w.trend * t
              + w.interest * i_contrib,
        breakdown={"skill": s, "trend": t,
                   "interest": i},
        gap=skills_gap(profile, role),
        trend_coverage=coverage,
    )
```

> **Learning cost.** 92 ÷ 104 = 88.5% of courses are free. The median of the plan hours 0.3, 7.7, 9.9, 14.5 and 17.5 is 9.9 hours.

## 5. Market Viability & Future Scalability Plan

SDC aims to encourage solutions that transition from innovations into market-ready applications. If given access to corporate funding, industry grants, or partnership opportunities (e.g., through SDC's Rotary network or joint research initiatives at XMUM), how would your team scale this prototype to process real-world data at volume?

[Maximum 250 words]

<!-- answer:start final-market limit=250 -->
> Our bottom-up estimate puts the serviceable Malaysian market at RM149 million a year: 620,000 highly impacted jobs at a blended RM240 per seat. The goal is about 1% of that by 2029, or RM1.5 million in recurring revenue from 5,500 seats and six campuses. These are projections, not traction.

> A proposed RM700,000 over 24 months would fund four stages, each released on a measured result:

> • 2027, first half: a 12-week paid pilot with one business-services team, plus the human time-to-plan study.

> • 2027, second half: Malaysian data partnerships, three new job families and five employers, because 38% of openings map to our roles today.

> • 2028: HR-system links, single sign-on, a formal PDPA review and security testing, and 25 employers.

> • 2029: 60 employers and a study of a second ASEAN market.

> The architecture suits volume because matching and plans read stored records and make no paid AI call. Trend inference runs as a weekly batch that costs nothing while idle, and the assistant can fall back to a fixed guide. Our model shows seats growing 110 times while infrastructure cost grows 12 times. Load testing would confirm this before each stage.

> Partners would supply what funding cannot: employers for pilots, TalentCorp and MYFutureJobs for Malaysian labour data, HRD Corp guidance on levy eligibility, and XMUM or Rotary links for joint evaluation. These are targets, not agreements.
<!-- answer:end final-market -->

## 6. Final Submission Checklist

Tick all boxes that apply before submitting.

☐ The application is fully compiled, live, and accessible via the deployment link provided in Section 1.

☑ The GitHub (or equivalent) repository contains a clean, well-documented README with installation instructions.

☑ The GitHub (or equivalent) repository shows the history of incremental code updates made throughout the official live hacking window.

☐ The final pitch deck has been exported and saved as a flattened PDF file.

☐ All fields in this template have been completed and word limits respected.

## 7. IP & Originality Declaration

7.1 Pre-Existing / Prior-Owned Work

Does this submission include any code, design, research, or other work that any team member created or owned before the start of this hackathon?

☐ Yes ☐ No ☑ No change from Phase 1 declaration

If yes, briefly describe what was pre-existing and which team member(s) owned it:

> Not applicable. The Phase 1 answer was No. The team consulted KerjaCerdas, a project belonging to another team, for general security concepts only; it reused no code from that project.

7.2 Third-Party Code, Datasets, or Models

Does your project use any third-party code libraries, open-source frameworks, public/private datasets, or pre-trained AI models that your team did not create?

☑ Yes ☐ No ☐ No change from Phase 1 declaration

If yes, list them below (open-source use is permitted provided it is declared and properly licensed/attributed):

| Name | Type (code/dataset/model) | License |
|---|---|---|
| Python, Python standard library | code | PSF-2.0 |
| Node.js, pnpm | code | MIT |
| Next.js, React, React DOM | code | MIT |
| TypeScript | code | Apache-2.0 |
| Tailwind CSS, @tailwindcss/postcss | code | MIT |
| next-intl, Three.js, Recharts | code | MIT |
| Inter via @fontsource-variable/inter | code (font) | MIT package; OFL-1.1 font |
| lucide-react | code | ISC |
| class-variance-authority | code | Apache-2.0 |
| clsx, tailwind-merge | code | MIT |
| openapi-fetch, openapi-typescript | code | MIT |
| FastAPI, Pydantic, pydantic-settings | code | MIT |
| Uvicorn, HTTPX | code | BSD-3-Clause |
| psycopg 3, psycopg-pool | code | LGPL-3.0-only |
| python-multipart | code | Apache-2.0 |
| PyMuPDF | code | AGPL-3.0 or Artifex commercial |
| PostgreSQL 16, pgvector | code | PostgreSQL License |
| RunPod Python SDK | code | MIT |
| sentence-transformers, Transformers | code | Apache-2.0 |
| PyTorch | code | BSD-3-Clause |
| pytest, Ruff, ESLint, eslint-config-next, Prettier, PyYAML, actionlint, Mermaid | code | MIT |
| uv | code | MIT or Apache-2.0 |
| Playwright | code | Apache-2.0 |
| Docker Engine and Compose | code | Apache-2.0 (open-source parts) |
| all-MiniLM-L6-v2 (pinned revision) | model | Apache-2.0 |
| GLM-5.3 via RunPod | model | Provider and model terms |
| Gemini 3.5 Flash Lite, 3.6 Flash, 3.1 Flash Lite; Gemini Embedding 001 | model | Google Gemini API terms |
| arXiv cs.AI feed and query API | dataset | arXiv terms |
| U.S. BLS Employment Projections 2023-2033 | dataset | U.S. government data; cite BLS |
| O*NET 31.0 crosswalk | dataset | CC BY 4.0, with stated exceptions |
| UN SDG Goal and Target APIs | dataset | UN data terms |
| OpenDOSM monthly Labour Force Survey | dataset | CC BY 4.0 |
| TalentCorp MyCOL 2024/2025 | dataset | TalentCorp publication terms |
| Public job feeds: Greenhouse, Lever, Ashby, Workday, Jibe, Himalayas, Jobicy, Remote OK, Remotive | dataset | Each source's terms |
| Certification pages: Microsoft, AWS, Google Cloud, IIBA, IAPP | dataset | Issuer terms |
| Microsoft Learn Catalog API, Coursera API and pages, Malaysian provider course pages | dataset | Each provider's terms |
| Bank Negara Malaysia exchange-rate API | dataset | BNM terms |
| Curated skill, course and SDG mappings; synthetic personas and CVs | dataset | Team-created; upstream rights retained |

> The Technical & Tools Declaration gives versions and purposes for these items.

7.3 Employment-Related IP Conflicts

Is any team member currently bound by an employment, internship, or consulting agreement under which their employer could claim ownership of work they create during this hackathon?

☐ Yes ☐ No ☑ No change from Phase 1 declaration

If yes, please describe the nature of the agreement and which member it concerns:

> Not applicable. The Phase 1 answer was No.

## 8. Declaration

By submitting this report, the team leader confirms that the deployed application and data presented above are the original work of the team, completed within the official SDC 2026 hackathon period.

[Signature]

[Date]
