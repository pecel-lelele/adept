# SDC HACKATHON 2026

Technical & Tools Declaration

Hosted by XMUM AI Club

Submission Deadline: 1st November 2026

## 1. Team & Project Overview

| Field | Response |
|---|---|
| Team Name | Pecel Lele |
| Project / Solution Name | Adept |
| Name (Leader) | David Kurniawan (team record) |
| Email & Phone (Leader) | PRIVATE COMPLETION REQUIRED in the organiser's submission copy. |
| University Affiliation(s) | Xiamen University Malaysia (team record) |
| Live Prototype URL | https://adept-my.replit.app (previously accessible; deployed revision and snapshot unverified against source `main` at `0a7868c`, 31 October 2026) |
| Code Repository URL (public / access granted to judges) | https://github.com/pecel-lelele/adept |

## 2. Architecture & Technology Stack

### 2.1 System Architecture Overview [Maximum 200 words]

<!-- answer:start technical-2.1 limit=200 -->
Next.js serves a multilingual public interface and proxies requests to private FastAPI. Signed accounts and membership checks protect workspaces. Replit's managed PostgreSQL stores profiles, reference catalogues, snapshots, programmes and progress; local/CI use PostgreSQL with pgvector. The launcher checks API/database readiness; it does not migrate or seed on startup.

Daily GitHub Actions sends an authenticated clock signal to the deployed app. Its shared worker uses its own database connection to retrieve public research, job feeds and course facts, run bounded checks, call the dedicated RunPod MiniLM endpoint for research embeddings, and atomically publish validated dated results. Page reads reuse stored results. Historical fixtures and source outages must be visibly disclosed. Deterministic matching and pathways combine confirmed skills with catalogue records and scenario estimates. Optional Gemini embeddings suggest unfamiliar skills, subject to user confirmation. Optional GLM-5.3 with Gemini failover selects checked Adi answer IDs; server-authored text is displayed.

This is the implemented source architecture, not proof of a production daily refresh. The old GitHub runner could not reach a private Replit database host; the new path needs deployment, required migrations and a successful publication check.
<!-- answer:end technical-2.1 -->

Block flow: public sources → app-side bounded worker (+ RunPod encoder) → validated PostgreSQL snapshot → private FastAPI → Next.js; signed workspaces → deterministic role/pathway/SDG views.

### 2.2 Languages, Frameworks & Libraries

| Name & Version | Purpose in Project | License |
|---|---|---|
| Python 3.11; Node.js 24; pnpm 10.29.3 | API/runtime, frontend tooling | PSF; Node MIT; pnpm MIT |
| Next.js 16.4.2; React/React DOM 19.3.1; TypeScript 5.9.3 | Public UI, proxy, types | Next/React MIT; TypeScript Apache-2.0 |
| Tailwind CSS and PostCSS 4.1.18; class-variance-authority 0.7.1; clsx 2.1.1; tailwind-merge 3.3.1 | Styling and UI variants | MIT except class-variance-authority Apache-2.0 |
| next-intl 4.14.9; Recharts 2.15.4; Three.js 0.180.0; lucide-react ^1.61.0 | Languages, charts, mascot, icons | MIT for next-intl/Recharts/Three; ISC for lucide |
| @fontsource-variable/inter ^5.3.0 | Bundled font assets (current UI uses system fallbacks) | Package MIT; Inter font SIL OFL 1.1 |
| openapi-fetch 0.14.1; openapi-typescript 7.9.1 | Generated typed API client | MIT |
| FastAPI >=0.161.1; Pydantic v2, pydantic-settings >=2.16.1; Uvicorn >=0.54 | API, validation, ASGI | MIT; Uvicorn BSD-3-Clause |
| psycopg[binary] >=3.3.6; psycopg-pool >=3.3.3; PostgreSQL 16 + pgvector | Relational/embedding storage | psycopg LGPL-3.0 and bundled notices; PostgreSQL License |
| PyMuPDF <2; python-multipart >=0.0.32; HTTPX >=0.28.1 | PDF/CV parsing, uploads, external requests | PyMuPDF AGPL-3.0 or Artifex commercial; multipart Apache-2.0; HTTPX BSD-3-Clause |
| RunPod SDK 1.12.0; sentence-transformers 6.2.0; Transformers 5.20.2; PyTorch 2.14.1 | Hosted MiniLM worker build/runtime; deployed image must be checked | RunPod MIT; sentence-transformers/Transformers Apache-2.0; PyTorch BSD-3-Clause |
| pytest >=9.1.1, Ruff >=0.17.2, ESLint 9.39.5; uv; Mermaid 11.12.0, PyYAML 6.0.3, actionlint 1.7.7, Prettier ^3.9.10, Playwright | Tests, package/tooling and diagrams | Upstream package terms; predominantly MIT; Playwright Apache-2.0; uv MIT or Apache-2.0 |

Versions are from source manifests and locks, not an attested deployed package inventory; licence terms for binaries and transitive dependencies require independent review.

Docker Compose is **local development tooling**, not a cloud host; Docker Desktop terms may differ. Review PyMuPDF's AGPL/commercial terms and transitive notices before attesting licence compliance. Adept's own Apache-2.0 licence does not override them.

## 3. APIs & Cloud Services

### 3.1 External APIs

| API & Provider | Purpose in Project | Access Tier (free / paid / sponsor-provided) |
|---|---|---|
| arXiv query API for completed cs.AI weeks; RSS in legacy/manual tooling | Public research observations; historical 2024 replay stays labelled historical | Public/free; terms and rate limits |
| UN Statistics SDG Goal/Target API | Official definitions and source audits, not endorsement of Adept's links | Public/free |
| Microsoft Learn Catalog API; Coursera courses API; provider HTTPS pages | Course availability and manually dated duration/fees | Public endpoint/pages; provider terms, not a resale licence |
| Bank Negara Malaysia OpenAPI | Currency conversion facts for priced learning | Public/free |
| Greenhouse, Lever, Ashby | Documented employer feeds, location-filtered for Malaysian automatic aggregate counts | Public endpoints; reuse rights not blanket-granted |
| Himalayas, Jobicy, Remote OK, Remotive; legacy Workday/Jibe | Dated remote postings in the automatic jobs path; legacy historical exports / CLI-only connectors are not the automatic local-count path | Public access with individual provider terms |
| Careerjet, Jooble, Web3.career | Optional keyed job connectors; historical fetch log marks keys/skips; not needed for automatic path | Keyed; terms and price/activation unverified |
| OpenDOSM monthly LFS | Malaysian national labour context only, not role-level vacancy demand | Public CC BY 4.0 |
| RunPod Serverless (separate Adi GLM-5.3 endpoint and MiniLM worker) | Optional chat answer selection; batch research embeddings | Sponsor credits apply temporarily; usage billed per applicable service |
| Google Gemini API (3.5 Flash Lite; 3.6 Flash; 3.1 Flash Lite; embedding-001) | Optional Adi failover and unfamiliar-skill suggestions; `auto` trend-matcher selection waits for an equivalence report, but explicit Gemini override does not | Free/paid tier depends on account; activation unverified |

The **US BLS 2023–2033 baseline** is a committed dated extract, not an API called per user. Model weights are downloaded from Hugging Face during the worker build; the service runs on RunPod. Public reachability does not grant unlimited redistribution rights. No API keys are listed.

### 3.2 Cloud Platforms & Deployment

| Service & Provider | Purpose in Project | Plan / Region |
|---|---|---|
| Replit Autoscale | Public web and loopback private API at https://adept-my.replit.app | Sponsor-provided Core subscription; screenshot shows Asia / 2 vCPU / 4 GiB at capture time, **not verified today** |
| Replit integrated PostgreSQL | Separate development/production managed relational databases | Current starting constraint; actual active plan, bill and backup policy unverified |
| RunPod Serverless and hosted model endpoint | MiniLM worker and optional GLM-5.3 Adi; earlier Pod test was a separate historical workload | Team-recorded US$25 sponsor credits; current region/GPU/bill unknown |
| GitHub repository, Actions and GHCR | Code, CI, daily clock-trigger workflow, image registry and manual fallback refresh | Public repo / GitHub-hosted runners; private DB host not reachable from ordinary GitHub runners |
| Local Docker Compose | PostgreSQL/pgvector development and tests only | Local, not deployment |

The Replit proof PDF shows historical hosting/database screens and **US$6.38 account spend in a displayed billing window**, not an Adept-only current expense. The RunPod proof PDF shows an earlier 110-skill, 0.354-second Pod vectorization test and Serverless setup; neither proves today's 142-skill catalogue was refreshed or a production trend snapshot published. Do not extrapolate those screenshots to cost per learner.

## 4. AI Tools, Models & Datasets

### 4.1 AI Models Used in the Solution

| Model & Version | Source / Provider | Usage (pre-trained / fine-tuned / self-trained) | License / Terms |
|---|---|---|---|
| all-MiniLM-L6-v2, pinned revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Sentence Transformers weights on team's RunPod Serverless worker | Pre-trained; no fine-tuning; 384-dimensional public paper/skill embeddings | Apache-2.0 |
| GLM-5.3 (`glm-5.3`) | RunPod-hosted model for optional Adi selection | Pre-trained hosted inference; **selects answer IDs**, not unchecked prose | Hosted provider/model terms; verify exact entitlement |
| Gemini 3.5 Flash Lite; 3.6 Flash; 3.1 Flash Lite | Google optional failover chain | Pre-trained hosted Adi inference; configured does not establish live invocation | Gemini API Terms |
| `gemini-embedding-001` | Google optional embedding path | Pre-trained 768-dimensional suggestions and gated trend matcher; no team fine-tuning | Gemini API Terms |

**Trend method:** source arXiv submissions + dated US BLS extract → cleaning/bounded sampling → sentence embeddings/mention counts → heuristic research velocity and Moderate/Fast scoring → coverage/date/ID validation → stored snapshot. In the default `auto` mode, a passing model-specific equivalence report is required before choosing Gemini. An operator can explicitly set `TRENDS_MATCHER=gemini` **without that gate**; that override must not be represented as equivalence-validated. Stored windows still keep methods separate. Research attention is **not** observed Malaysian labour demand, and scenario bands are **not** calibrated confidence intervals.

### 4.2 Datasets

The counts here are **source CSV rows inspected 31 October 2026**, not a deployed-database count. Taxonomy: **142 skills, 48 stored roles of which 33 `is_target=true`, 104 course rows**; role/skill links are reviewed curations. Historical screenshots and a 20 October synthetic impact fixture list smaller earlier catalogue sizes. No team-trained model or real CV dataset is declared.

| Dataset Name | Source / URL | Type (public / private / self-collected / synthetic) | License | Personal Data? (Y/N) |
|---|---|---|---|---|
| Curated roles/skills, requirements and O*NET 31.0 crosswalk | Team-curated records; O*NET https://www.onetcenter.org/ | Team-curated + public-derived | O*NET CC BY 4.0 with exceptions; edited requirements are estimates | N |
| arXiv cs.AI papers and dated stored mention inputs | arXiv public API https://info.arxiv.org/help/api/ | Public metadata / sampled extracts | Metadata/content have distinct rights; raw publications may contain author names | Y (public author names may occur upstream; no learner records) |
| US BLS 2023–2033 occupation projections | US BLS https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm | Public / derived | US government source; US-only baseline, not a Malaysian job forecast | N |
| Historical 2024 trend replay and synthetic trend fallback | Team-created historical replay from dated arXiv metadata and synthetic fallback | Public-derived / synthetic fixture | Estimated model values, labelled historical/fixture | N |
| UN 17 goals, 169 targets; team mappings | UN Statistics SDG API https://unstats.un.org/SDGAPI/v1/sdg/Goal/List | Public definitions + team-curated 88 role and 167 skill link rows | UN terms; mappings are team hypotheses, not official approval | N |
| 104 curated courses and prerequisites | Microsoft Learn https://learn.microsoft.com/en-us/training/support/catalog-api ; Coursera https://api.coursera.org/api/courses.v1 ; other cited providers | Public facts + team curation | Content/fees/provider rights remain with providers; claimability must be checked | N |
| 1,175 source job-posting rows; certification and FX extracts | Greenhouse https://developers.greenhouse.io/job-board.html ; Lever https://github.com/lever/postings-api ; Ashby https://developers.ashbyhq.com/docs/public-job-posting-api ; BNM https://api.bnm.gov.my/ | Public/curated | Board and cert issuer rights apply; older ads may close | N for learner data; postings may name employers |
| OpenDOSM national monthly LFS; MyCOL 2024/25 groups | DOSM https://data.gov.my/data-catalogue/lfs_month ; TalentCorp https://www.talentcorp.com.my/resources/publications/mymahir-malaysia-critical-occupations-list-mycol20242025/ | Public aggregates / reviewed crosswalk | DOSM CC BY 4.0; TalentCorp terms; historical MyCOL badge does not affect ranking | N |
| Synthetic demonstration profiles, employers, CVs and regression fixtures | Team-created synthetic examples; no outside source URL | Synthetic | No actual personal CVs used in the competition demonstration | N |

### 4.3 AI-Assisted Development Tools

Did your team use any generative-AI tool to help create code, design, text, or other project material?

[x] Yes [ ] No

| Tool & Version | Used For | Extent of Use (minor / moderate / major) |
|---|---|---|
| Anthropic Claude Code; model versions varied / not fully recorded | Primary code generation, documentation and presentation planning | Major |
| OpenAI Codex; exact model versions not fully recorded | Debugging, implementation review and code/document corrections | Major |
| Replit Agent; version unrecorded | Repository exploration | Minor |
| Google Antigravity agent; version unrecorded | Repository exploration | Minor |
| Greptile; version unrecorded | PR review | Moderate |
| Remotion 4.0.538, ElevenLabs voiceover, Mixkit and Google Fonts | Demo/pitch production only; exact exported Mixkit assets/font/take credits require team confirmation | Presentation tooling; actual extent to verify |

Briefly describe how your team reviewed, tested, and took responsibility for AI-generated output: [Maximum 100 words]

<!-- answer:start technical-4.3 limit=100 -->
The team set Adept's product direction; Claude Code produced much of the source and presentation drafts. Codex helped debug and review; other tools supported inspection and PR feedback. Team members remain responsible for all accepted code and claims. The source is checked against tests, source records and dates; test success does not verify a deployed build or customer benefit. The team must inspect the final media assets, licensing notices and all members' tool usage before signing. Model output never authorises invented catalogue entries or personnel decisions.
<!-- answer:end technical-4.3 -->

The voiceover service is a **presentation service**, not a model inside Adept. The synthesis model and final exported takes remain unrecorded. Do not declare unconfirmed installed plugins as used services.

## 5. Sponsor-Provided Resources

Did your project use any official SDC sponsor-provided resource?

[x] Yes [ ] No

Team-recorded Replit Core subscription and RunPod **US$25** credits; exact remaining balances and eligibility periods need account confirmation. Sponsorship is not permanent free production hosting.

| Sponsor | Resource (API / credits / platform / data) | How It Was Used in the Project |
|---|---|---|
| Replit | Core subscription, Autoscale deployment, managed PostgreSQL | Public prototype, private API and persistent app records; Replit Agent exploration declared above. |
| RunPod | US$25 credits, historical RTX 4090 Pod batch, separate Serverless MiniLM and GLM-5.3 service | Model inference/worker testing; successful Pod batch does not prove new trend publication. |

Was the sponsor resource essential to the core functionality of the prototype, or could it be replaced? Explain briefly: [Maximum 100 words]

<!-- answer:start technical-5 limit=100 -->
Replit is the prototype's current web/API and managed-PostgreSQL host; RunPod provides MiniLM encoding and optional Adi inference. Neither sponsor's credit is a viable permanent business model. Replacing Replit would require migrating the same schema, signed-session boundaries and backups; replacing MiniLM requires a method-equivalence check before changing any scored series. The learner's normal matching and plan reads are deterministic and do not require per-page model calls. Provider outages preserve dated data or show unavailable states, subject to the actual deployment configuration.
<!-- answer:end technical-5 -->

## 6. Security, Privacy & Responsible Use

### 6.1 Data Handling & Privacy [Maximum 150 words]

<!-- answer:start technical-6.1 limit=150 -->
The demo uses synthetic identities and CVs, not real applicants. Signed accounts can store names/emails, password hashes, confirmed skills, preferences, memberships, plans, progress and evidence links in PostgreSQL. CV bytes are parsed in memory and not retained. Members explicitly opt in to share skills/progress; personal plans and assistant conversations stay separate. Authentication, server-side membership/manager checks, upload limits, bounded network access and HTTP-only signed cookies mitigate risks.

Optional Gemini suggestions receive short contact-redacted skill phrases. Optional Adi providers receive filtered context and server-authored candidate blocks; redaction cannot guarantee that no personal information leaves the service. MiniLM receives public research/catalogue text. Account export and deletion exist, but automatic retention, tested backup erasure and contractual real-user processing arrangements are **not** established. Do not claim PDPA certification or use real CVs in the demo.
<!-- answer:end technical-6.1 -->

### 6.2 Known Limitations & Risks [Maximum 150 words]

<!-- answer:start technical-6.2 limit=150 -->
arXiv research share and a US labour baseline cannot measure Malaysian occupation demand. Historical 2024 replay is not fresh evidence; an online check can leave observations unchanged. Scenarios and skill exposure are heuristics, not calibrated probabilities. The catalogue covers selected roles/courses; fees, openings, prerequisites and HRD claimability can change. A completion click is not verified competence or a regulated qualification. SDG links are draft enabling hypotheses, not measured UN outcomes.

Source dates, estimate/fallback labels, ID validation, permissions, bounded workers, stale states and human confirmation mitigate risks; they do not prove universal fairness. A successful model call does not publish data. A local test, public HTTP 200 or sponsor screenshot cannot establish the deployed revision, current observations, vendor licences or customer outcomes. Verify each separately before commercial use.
<!-- answer:end technical-6.2 -->

## 7. Compliance & Readiness Checklist

- [ ] All APIs, cloud services, AI tools, models, and datasets used in the project are declared in this document.
- [ ] All third-party code, datasets, and models are used in accordance with their licenses, and attribution is provided where required.
- [ ] No API keys, passwords, or other credentials are exposed in the code repository, prototype, or this document.
- [ ] Any use of generative-AI tools for development has been disclosed and reviewed by the team.
- [x] Any use of official SDC sponsor resources has been declared in Section 5.
- [ ] The prototype described here is accessible to judges through the links provided in Section 1.
- [ ] All fields in this template have been completed within the word limits stated.

## 8. Declaration

By submitting this document, the team leader confirms that the information provided is complete and accurate to the best of the team's knowledge, and that every API, cloud service, AI tool, dataset, model, and sponsor resource used in the project has been declared.

[Signature]

[Date]
