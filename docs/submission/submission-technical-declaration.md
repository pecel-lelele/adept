# SDC HACKATHON 2026

Technical & Tools Declaration

Hosted by XMUM AI Club

Submission Deadline: 1st November 2026

## 1. Team & Project Overview

| Field | Response |
|---|---|
| Team Name | Pecel Lele |
| Project / Solution Name | Adept |
| Name (Leader) | David Kurniawan |
| Email & Phone (Leader) | [To be completed by team leader] |
| University Affiliation(s) | Xiamen University Malaysia |
| Live Prototype URL | https://adept-my.replit.app |
| Code Repository URL (public / access granted to judges) | https://github.com/pecel-lelele/adept |

## 2. Architecture & Technology Stack

### 2.1 System Architecture Overview [Maximum 200 words]

<!-- answer:start technical-2.1 limit=200 -->
Next.js serves a multilingual public interface and proxies requests to a private FastAPI service. Signed accounts and membership checks protect workspaces. Replit's managed PostgreSQL stores profiles, reference catalogues, snapshots, programmes and progress; local development and CI use PostgreSQL with pgvector. The launcher checks API and database readiness; it does not migrate or seed on startup.

A daily GitHub Actions schedule sends an authenticated trigger to the deployed application. Its shared worker uses its own database connection to retrieve public research, job feeds and course facts, run bounded checks, call the dedicated RunPod MiniLM endpoint for research embeddings, and atomically publish validated, dated results. Page reads reuse stored results. Historical fixtures and source outages are labelled in the interface. Deterministic matching and pathways combine confirmed skills with catalogue records and scenario estimates. Optional Gemini embeddings suggest unfamiliar skills, subject to user confirmation. Optional GLM-5.3 with Gemini failover selects checked Adi answer IDs; only server-authored text is displayed.

The original GitHub runner could not reach Replit's private database host, so refresh moved into the application; production activation is confirmed by the first successful scheduled publication.
<!-- answer:end technical-2.1 -->

Block flow: public sources → application-side bounded worker (with RunPod encoder) → validated PostgreSQL snapshot → private FastAPI → Next.js; signed workspaces → deterministic role, pathway and SDG views.

### 2.2 Languages, Frameworks & Libraries

| Name & Version | Purpose in Project | License |
|---|---|---|
| Python 3.11; Node.js 24; pnpm 10.29.3 | API and pipeline runtime; web runtime and package management | Python PSF-2.0; Node.js MIT; pnpm MIT |
| Next.js 16.4.2; React and React DOM 19.3.1; TypeScript 5.9.3 | Public web interface, server-side proxy and static typing | Next.js and React MIT; TypeScript Apache-2.0 |
| Tailwind CSS 4.1.18 (with its PostCSS plugin 4.1.18); class-variance-authority 0.7.1; clsx 2.1.1; tailwind-merge 3.3.1 | Styling and UI component variants | MIT, except class-variance-authority Apache-2.0 |
| next-intl 4.14.9; Recharts 2.15.4; Three.js 0.180.0; lucide-react 1.61.0 | English, Malay and Chinese interface; chart components; 3D Adi mascot; icons | next-intl, Recharts and Three.js MIT; lucide-react ISC |
| Inter variable font package 5.3.0 (Fontsource) | Installed font package; the current interface renders with system fonts | SIL Open Font License 1.1 |
| openapi-fetch 0.14.1; openapi-typescript 7.9.1 | Typed API client generated from the API contract | MIT |
| FastAPI 0.161.1; Pydantic 2.14.1; pydantic-settings 2.16.1; Uvicorn 0.54.0 | API framework, strict validation, configuration and ASGI server | FastAPI and Pydantic MIT; Uvicorn BSD-3-Clause |
| psycopg 3.3.6 (binary) and psycopg-pool 3.3.3; PostgreSQL 16 with pgvector | Relational and vector storage, connection pooling | psycopg LGPL-3.0; PostgreSQL and pgvector PostgreSQL License |
| PyMuPDF 1.28.2; python-multipart 0.0.32; HTTPX 0.28.1 | CV text extraction (PDF), file uploads, outbound requests | PyMuPDF AGPL-3.0 or Artifex commercial licence; python-multipart Apache-2.0; HTTPX BSD-3-Clause |
| RunPod SDK 1.12.0; sentence-transformers 6.2.0; Transformers 5.20.2; PyTorch 2.14.1 | Hosted MiniLM embedding worker (separate container image) | RunPod SDK MIT; sentence-transformers and Transformers Apache-2.0; PyTorch BSD-3-Clause |
| pytest 9.1.1; Ruff 0.17.2; ESLint 9.39.5; Playwright 1.64.1; Prettier 3.9.10; PyYAML 6.0.3; actionlint 1.7.7; uv | Tests, linting, formatting, browser journeys, workflow checks and Python environments | MIT, except Playwright Apache-2.0 and uv MIT or Apache-2.0 |

Versions are those pinned in the project's lock files and installed in the development environment on 1 November 2026; they are not an attested inventory of the deployed container. Licences were read from installed package metadata where available.

Docker Compose is used only as local development tooling for the database, not as a cloud host. PyMuPDF's AGPL-3.0 terms require review, or a commercial licence, before commercial distribution; Adept's own Apache-2.0 licence does not override third-party terms.

## 3. APIs & Cloud Services

### 3.1 External APIs

| API & Provider | Purpose in Project | Access Tier (free / paid / sponsor-provided) |
|---|---|---|
| arXiv API (Cornell University), cs.AI listings | Public research observations for trend signals; the October 2024 replay stays labelled historical | Free public API, subject to arXiv terms and rate limits |
| UN Statistics Division SDG API | Official goal and target definitions; Adept's links are team alignments, not UN endorsement | Free public API |
| Microsoft Learn Catalog API; Coursera course API; course provider web pages | Course availability, duration and fees, with retrieval dates | Free public endpoints; provider terms apply, no resale licence |
| Bank Negara Malaysia Open API | Exchange rates for course prices quoted in foreign currency | Free public API |
| Greenhouse, Lever and Ashby public job-board APIs | Documented employer job feeds, filtered to Malaysian locations for automatic aggregate counts | Free public endpoints; reuse rights are not blanket-granted |
| Himalayas, Jobicy, Remote OK, Remotive | Dated remote job postings in the automatic jobs path | Free public access under each provider's terms |
| SmartRecruiters, Workday and Jibe career sites | Legacy connectors in the stand-alone command-line tool only; not used by the automatic refresh | Free public pages under each provider's terms |
| Careerjet, Jooble, Web3.career | Optional keyed job connectors; skipped when no key is configured and not required by the automatic path | Keyed access; activation and pricing not established |
| OpenDOSM monthly Labour Force Survey | Malaysian national labour context only, not role-level vacancy demand | Free public data, CC BY 4.0 |
| RunPod Serverless (separate MiniLM endpoint and GLM-5.3 Adi endpoint) | Batch research embeddings; optional Adi answer selection | Sponsor-provided credits, then pay per use |
| Google Gemini API (3.5 Flash Lite, 3.6 Flash, 3.1 Flash Lite; gemini-embedding-001) | Optional Adi failover and unfamiliar-skill suggestions; optional trend matcher after an equivalence test | Free or paid tier depending on the account; off by default |
| GitHub REST API (workflow dispatch) | Optional administrator fallback that starts the trend-refresh workflow | Free with a scoped token |

The **US BLS 2023–2033 projections** are a committed, dated extract, not an API called per user. MiniLM model weights are downloaded from Hugging Face when the worker image is built; the model runs on RunPod. Public reachability does not grant unlimited redistribution rights. No API keys are listed in this document.

### 3.2 Cloud Platforms & Deployment

| Service & Provider | Purpose in Project | Plan / Region |
|---|---|---|
| Replit Autoscale | Public web server and private loopback API for the live prototype | Sponsor-provided Replit Core subscription; Asia region, 2 vCPU / 4 GiB at the time of the proof-of-use capture |
| Replit managed PostgreSQL | Separate development and production relational databases | Usage-billed under the Replit account; backup policy not yet tested |
| RunPod Serverless | MiniLM embedding worker and optional GLM-5.3 Adi endpoint; an earlier GPU Pod test was a separate one-off workload | Pay-per-use Serverless funded by US$25 sponsor credits; region not recorded |
| GitHub repository, GitHub Actions and GitHub Container Registry | Source code, CI, daily refresh trigger, worker image registry and manual fallback refresh | Public repository on GitHub-hosted runners (free tier) |
| Docker Compose (local) | PostgreSQL with pgvector for development and tests only | Local machine, not deployment |

The Replit proof-of-use screenshots show hosting and database screens and **US$6.38 account spend in one displayed billing window**, not an Adept-only running cost. The RunPod proof-of-use screenshots show an earlier 110-skill, 0.354-second Pod vectorisation test and the Serverless set-up; they do not show that today's 142-skill catalogue was refreshed in production. Neither represents a per-learner cost.

## 4. AI Tools, Models & Datasets

### 4.1 AI Models Used in the Solution

| Model & Version | Source / Provider | Usage (pre-trained / fine-tuned / self-trained) | License / Terms |
|---|---|---|---|
| all-MiniLM-L6-v2 (Sentence Transformers), pinned to a fixed Hugging Face revision | Hugging Face weights served by the team's RunPod Serverless worker | Pre-trained, not fine-tuned; 384-dimensional embeddings of public papers and catalogue skills | Apache-2.0 |
| GLM-5.3 (Z.ai) | Hosted through RunPod for optional Adi answer selection | Pre-trained hosted inference; **selects answer-block IDs only**, never displayed prose | Z.ai model terms and RunPod terms |
| Gemini 3.5 Flash Lite; Gemini 3.6 Flash; Gemini 3.1 Flash Lite | Google Gemini API, optional failover chain for Adi | Pre-trained hosted inference; off by default | Gemini API Terms of Service |
| gemini-embedding-001 | Google Gemini API, optional embedding path | Pre-trained; 768-dimensional unfamiliar-skill suggestions and an optional trend matcher; no fine-tuning | Gemini API Terms of Service |

**Trend method:** arXiv cs.AI submissions and a dated US BLS extract → cleaning and bounded sampling → sentence embeddings and mention counts → heuristic research velocity and Moderate/Fast scenario scoring → coverage, date and ID validation → stored, dated snapshot. By default the trend matcher uses MiniLM and switches to Gemini embeddings only after a passing method-equivalence report; an operator can force Gemini manually, in which case the series is not equivalence-validated and is stored separately. Research attention is **not** observed Malaysian labour demand, and scenario bands are **not** calibrated confidence intervals. The default runtime uses no language model.

### 4.2 Datasets

Counts are **rows in the source catalogue files on 1 November 2026**, not a deployed-database count: **142 skills; 48 roles, of which 33 are target roles; 104 courses**. Role and skill links are reviewed team curations. Earlier proof-of-use screenshots and a 20 October 2026 synthetic impact fixture show smaller, earlier catalogue sizes. No team-trained model and no real CV dataset is used.

| Dataset Name | Source / URL | Type (public / private / self-collected / synthetic) | License | Personal Data? (Y/N) |
|---|---|---|---|---|
| Curated roles and skills, role requirements and O*NET 31.0 crosswalk | Team curation; O*NET Resource Center (U.S. Department of Labor) | Team-curated, public-derived | O*NET CC BY 4.0 with stated exceptions; edited requirement levels are Adept estimates | N |
| arXiv cs.AI paper metadata and dated mention counts | arXiv (Cornell University) | Public metadata, sampled extracts | arXiv metadata CC0 1.0; individual papers keep their own licences | Y (author names in public metadata; no learner records) |
| US occupational projections 2023–2033 | U.S. Bureau of Labor Statistics | Public, derived extract | U.S. Government public domain; US-only baseline, not a Malaysian forecast | N |
| Historical October 2024 trend replay and synthetic trend fallback | Team-created from dated arXiv metadata, plus a synthetic fallback | Public-derived and synthetic | Team-created; values labelled historical or fixture | N |
| UN SDG goals (17) and targets (169); team role (88) and skill (167) alignment rows | UN SDG API (UN Statistics Division); team curation | Public definitions and team-curated mappings | UN terms of use; mappings are team hypotheses, not official approval | N |
| 104 curated courses and skill prerequisites | Microsoft Learn; Coursera; other named course providers | Public facts and team curation | Content, fees and rights remain with providers; HRD claimability must be checked per course | N |
| 1,175 job-posting rows; certification list; exchange-rate extracts | Greenhouse, Lever and Ashby job boards; certification issuers; Bank Negara Malaysia | Public, curated | Job-board and issuer terms apply; older postings may have closed | N for learners; postings name employers |
| Monthly Labour Force Survey; MyCOL 2024/2025 critical occupations | OpenDOSM (Department of Statistics Malaysia); TalentCorp MyCOL | Public aggregates and reviewed crosswalk | OpenDOSM CC BY 4.0; TalentCorp terms; the MyCOL badge does not affect ranking | N |
| Synthetic demonstration profiles, employers, CVs and test fixtures | Team-created | Synthetic | Team-created | N |

### 4.3 AI-Assisted Development Tools

Did your team use any generative-AI tool to help create code, design, text, or other project material?

[x] Yes [ ] No

| Tool & Version | Used For | Extent of Use (minor / moderate / major) |
|---|---|---|
| Anthropic Claude Code (model versions varied over the project) | Code generation, debugging, documentation and submission drafting | Major |
| OpenAI Codex (model versions varied over the project) | Debugging, implementation review and code and document corrections | Major |
| Replit Agent | Replit deployment configuration, publishing and repository exploration | Minor |
| Google Antigravity agent | Repository exploration | Minor |
| Greptile | Automated pull-request review comments | Moderate |
| ElevenLabs (synthesis model/version not recorded) | Presentation/demo voice-over using a stock voice; the team confirmed historical use on 30 October 2026. Not an Adept runtime integration. | To be confirmed by the team |

Briefly describe how your team reviewed, tested, and took responsibility for AI-generated output: [Maximum 100 words]

<!-- answer:start technical-4.3 limit=100 -->
The team set Adept's product direction and reviewed changes through pull requests before merging. Claude Code produced much of the source and document drafts; Codex helped debug and review; Replit Agent, Antigravity and Greptile supported deployment set-up, inspection and pull-request feedback. Team members remain responsible for all accepted code and claims. Changes pass automated lint, type, contract, attribution and fairness tests and are checked against source records and dates; passing tests do not verify a deployed build or customer benefit. Model output never authorises invented catalogue entries or personnel decisions.
<!-- answer:end technical-4.3 -->

## 5. Sponsor-Provided Resources

Did your project use any official SDC sponsor-provided resource?

[x] Yes [ ] No

The team used a sponsor-provided Replit Core subscription and US$25 of RunPod credits. Sponsorship is not permanent free production hosting.

| Sponsor | Resource (API / credits / platform / data) | How It Was Used in the Project |
|---|---|---|
| Replit | Core subscription, Autoscale deployment, managed PostgreSQL | Public prototype, private API and persistent application records; Replit Agent use is declared in Section 4.3. |
| RunPod | US$25 credits; GPU Pod test; Serverless MiniLM and GLM-5.3 endpoints | Research embeddings and optional Adi inference; the one-off Pod test validated batch encoding. |

Was the sponsor resource essential to the core functionality of the prototype, or could it be replaced? Explain briefly: [Maximum 100 words]

<!-- answer:start technical-5 limit=100 -->
Replit is the prototype's current web, API and managed-PostgreSQL host; RunPod provides MiniLM encoding and optional Adi inference. Neither sponsor's credit is a viable permanent business model. Replacing Replit would require migrating the same schema, signed-session boundaries and backups; replacing MiniLM requires a method-equivalence check before changing any scored series. The learner's normal matching and plan reads are deterministic and do not require per-page model calls. Provider outages preserve dated data or show unavailable states, so the core journey continues without either model service.
<!-- answer:end technical-5 -->

## 6. Security, Privacy & Responsible Use

### 6.1 Data Handling & Privacy [Maximum 150 words]

<!-- answer:start technical-6.1 limit=150 -->
The demo uses synthetic identities and CVs, not real applicants. Signed accounts can store names, emails, password hashes, confirmed skills, preferences, memberships, plans, progress and evidence links in PostgreSQL. CV bytes are parsed in memory and not retained. Members explicitly opt in to share skills and progress; personal plans and assistant conversations stay separate. Authentication, server-side membership and manager checks, upload limits, bounded network access and HTTP-only signed cookies mitigate risks.

Optional Gemini suggestions receive short contact-redacted skill phrases. Optional Adi providers receive filtered context and server-authored candidate blocks; redaction cannot guarantee that no personal information leaves the service. MiniLM receives public research and catalogue text. Account export and deletion exist, but automatic retention, tested backup erasure and contractual real-user processing arrangements are **not** established. Adept does not claim PDPA certification, and no real CVs are used in the demo.
<!-- answer:end technical-6.1 -->

### 6.2 Known Limitations & Risks [Maximum 150 words]

<!-- answer:start technical-6.2 limit=150 -->
arXiv research share and a US labour baseline cannot measure Malaysian occupation demand. Historical 2024 replay is not fresh evidence; an online check can leave observations unchanged. Scenarios and skill exposure are heuristics, not calibrated probabilities. The catalogue covers selected roles and courses; fees, openings, prerequisites and HRD claimability can change. A completion click is not verified competence or a regulated qualification. SDG links are draft enabling hypotheses, not measured UN outcomes.

Source dates, estimate and fallback labels, ID validation, permissions, bounded workers, stale states and human confirmation mitigate risks; they do not prove universal fairness. A successful model call does not publish data. A local test, public HTTP 200 or sponsor screenshot cannot establish the deployed revision, current observations, vendor licences or customer outcomes. Each requires separate verification before commercial use.
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
