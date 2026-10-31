SDC HACKATHON 2026

Technical & Tools Declaration

Hosted by Xiamen University Malaysia (XMUM) AI Club

Submission Deadline: 1st November 2026

Instructions: Declare every API, cloud service, AI tool, dataset, model, and sponsor resource your team used to build the project. Complete every section; where a category does not apply, tick “No” or write “None” – do not leave it blank. Submit as a single PDF document named “SDC2026_TeamName_TechDeclaration.pdf” together with your project submission. Undeclared third-party resources discovered at judging may affect your score or eligibility.

## 1. Team & Project Overview

Team Name

> Pecel Lele

Project / Solution Name

> Adept

Name (Leader)

> David Kurniawan

Email & Phone (Leader)

> [To be completed in the signed version]

University Affiliation(s)

> Xiamen University Malaysia

Live Prototype URL

> [https://adept-my.replit.app](https://adept-my.replit.app)

Code Repository URL (public / access granted to judges)

> [https://github.com/pecel-lelele/adept](https://github.com/pecel-lelele/adept)

## 2. Architecture & Technology Stack

### 2.1 System Architecture Overview

Describe how the components declared in this document connect end-to-end (e.g., user interface → backend → AI model/API → database → cloud hosting). Attach a system block diagram as an appendix if available.

[Maximum 200 words]

<!-- answer:start technical-2.1 limit=200 -->
> Next.js serves a public interface in three languages and forwards requests to a private FastAPI service. Signed accounts and server-side membership checks protect each workspace. Replit's managed PostgreSQL stores profiles, reference catalogues, snapshots, programmes and progress; local development and CI use PostgreSQL with pgvector. A Python launcher checks API and database readiness and does not migrate or seed on startup.

> A daily GitHub Actions schedule sends an authenticated trigger to the deployed application. Its shared worker retrieves public research, job feeds and course facts, runs bounded checks, calls the dedicated RunPod MiniLM endpoint for research embeddings and publishes validated, dated results in one transaction. Page reads reuse stored results, and historical fixtures or source outages are labelled on screen.

> Deterministic matching and pathways combine confirmed skills with catalogue records and scenario estimates. Optional Gemini embeddings suggest unfamiliar skills, subject to user confirmation. Optional GLM-5.3, with Gemini failover, selects checked Adi answer IDs, and only server-written text is displayed.

> The system block diagram is in the appendix.
<!-- answer:end technical-2.1 -->

### 2.2 Languages, Frameworks & Libraries

List the main programming languages, frameworks, and third-party libraries that your team did not create. Open-source use is permitted provided it is declared and properly licensed/attributed.

| Name & Version | Purpose in Project | License |
|---|---|---|
| Python 3.11; Node.js 24; pnpm 10.29.3 | API and pipeline runtime; web runtime and package management | PSF-2.0; MIT; MIT |
| Next.js 16.4.2; React and React DOM 19.3.1; TypeScript 5.9.3 | Public web interface, server-side proxy and static typing | MIT; MIT; Apache-2.0 |
| Tailwind CSS and @tailwindcss/postcss 4.1.18; class-variance-authority 0.7.1; clsx 2.1.1; tailwind-merge 3.3.1 | Styling and UI component variants | MIT, except class-variance-authority Apache-2.0 |
| next-intl 4.14.9; Recharts 2.15.4; Three.js 0.180.0; lucide-react 1.61.0 | English, Malay and Chinese interface; chart components; 3D Adi mascot; icons | MIT, except lucide-react ISC |
| @fontsource-variable/inter 5.3.0 | Installed font package; the interface currently renders with system fonts | MIT package; OFL-1.1 font |
| openapi-fetch 0.14.1; openapi-typescript 7.9.1 | Typed API client generated from the API contract | MIT |
| FastAPI 0.161.1; Pydantic 2.14.1; pydantic-settings 2.16.1; Uvicorn 0.54.0 | API framework, strict validation, configuration and ASGI server | MIT, except Uvicorn BSD-3-Clause |
| psycopg 3.3.6 and psycopg-pool 3.3.3; PostgreSQL 16 with pgvector | Relational and vector storage, connection pooling | LGPL-3.0-only; PostgreSQL License |
| PyMuPDF 1.28.2; python-multipart 0.0.32; HTTPX 0.28.1 | CV text extraction and report export; file uploads; outbound requests | AGPL-3.0 or Artifex commercial; Apache-2.0; BSD-3-Clause |
| RunPod SDK 1.12.0; sentence-transformers 6.2.0; Transformers 5.20.2; PyTorch 2.14.1 | Hosted MiniLM embedding worker in a separate container image | MIT; Apache-2.0; Apache-2.0; BSD-3-Clause |
| pytest 9.1.1; Ruff 0.17.2; ESLint 9.39.5; eslint-config-next 16.4.2; Playwright 1.64.1; Prettier 3.9.10; PyYAML 6.0.3; actionlint 1.7.7; Mermaid 11.12.0; uv | Tests, linting, formatting, browser journeys, workflow checks, diagrams and Python environments | MIT, except Playwright Apache-2.0 and uv MIT or Apache-2.0 |
| Docker Engine and Compose | Local PostgreSQL for development and tests only | Apache-2.0 for open-source components |

> Versions come from the project's manifests and lock files on 1 November 2026. PyMuPDF's AGPL-3.0 terms need review, or a commercial licence, before commercial distribution.

## 3. APIs & Cloud Services

### 3.1 External APIs

List every external API your solution calls (GenAI, maps, payments, messaging, data feeds, etc.). Do not include API keys or secrets in this document.

| API & Provider | Purpose in Project | Access Tier (free / paid / sponsor-provided) |
|---|---|---|
| arXiv API (Cornell University), cs.AI listings | Public research observations for trend signals; the October 2024 replay stays labelled historical | Free public API |
| UN Statistics Division SDG API | Official goal and target definitions; Adept's links are team alignments, not UN endorsement | Free public API |
| Microsoft Learn Catalog API; Coursera course API; course provider web pages | Course availability, duration and fees, with retrieval dates | Free public endpoints; provider terms apply |
| Bank Negara Malaysia Open API | Exchange rates for course prices quoted in foreign currency | Free public API |
| Greenhouse, Lever and Ashby public job-board APIs | Employer job feeds, filtered to Malaysian locations | Free public endpoints |
| Himalayas, Jobicy, Remote OK, Remotive | Dated remote job postings | Free public access |
| Workday and Jibe career sites | Legacy connectors in the command-line tool, present in the committed job extract; not used by automatic refresh | Free public pages |
| Careerjet, Jooble, Web3.career | Optional keyed job connectors, skipped when no key is configured | Keyed access; not active |
| OpenDOSM monthly Labour Force Survey | Malaysian national labour context, not role-level demand | Free public data |
| RunPod Serverless: MiniLM endpoint and GLM-5.3 endpoint | Batch research embeddings; optional Adi answer selection | Sponsor-provided credits, then paid per use |
| Google Gemini API: 3.5 Flash Lite, 3.6 Flash, 3.1 Flash Lite, gemini-embedding-001 | Optional Adi failover and unfamiliar-skill suggestions; optional trend matcher after an equivalence test | Free or paid tier by account; off by default |
| GitHub REST API (workflow dispatch) | Optional administrator fallback that starts the trend-refresh workflow | Free with a scoped token |

> The U.S. BLS 2023-2033 projections are a committed, dated extract and are not called per user. MiniLM weights are downloaded from Hugging Face when the worker image is built, and the model runs on RunPod.

### 3.2 Cloud Platforms & Deployment

List every cloud service used for hosting, storage, databases, authentication, or compute, and indicate how the prototype is deployed.

| Service & Provider | Purpose in Project | Plan / Region |
|---|---|---|
| Replit Autoscale | Public web server and private API for the live prototype | Sponsor-provided Replit Core; Asia region, 2 vCPU and 4 GiB at the proof-of-use capture |
| Replit managed PostgreSQL | Separate development and production application databases; signed local accounts live here | Usage-billed under the Replit account |
| RunPod Serverless | MiniLM embedding worker and optional GLM-5.3 endpoint; an earlier GPU Pod test was a one-off | Pay per use from US$25 sponsor credits; region not recorded |
| GitHub repository, Actions and Container Registry | Source code, CI, daily refresh trigger, worker image and manual fallback refresh | Public repository on GitHub-hosted runners |
| Docker Compose (local) | PostgreSQL with pgvector for development and tests only | Local machine, not deployment |

> The prototype deploys from the repository root as one public Next.js server and one private FastAPI process, started by a Python supervisor.

## 4. AI Tools, Models & Datasets

### 4.1 AI Models Used in the Solution

List every AI model embedded in or called by your application, including pre-trained, fine-tuned, and self-trained models.

| Model & Version | Source / Provider | Usage (pre-trained / fine-tuned / self-trained) | License / Terms |
|---|---|---|---|
| all-MiniLM-L6-v2, revision 1110a243 | Hugging Face weights on the team's RunPod Serverless worker | Pre-trained; 384-dimensional embeddings of public papers and catalogue skills | Apache-2.0 |
| GLM-5.3 (Z.ai) | RunPod, for optional Adi answer selection | Pre-trained hosted inference; selects answer-block IDs only | Z.ai and RunPod terms |
| Gemini 3.5 Flash Lite, 3.6 Flash, 3.1 Flash Lite | Google Gemini API, optional Adi failover | Pre-trained hosted inference; off by default | Gemini API Terms |
| gemini-embedding-001 | Google Gemini API, optional | Pre-trained; 768-dimensional skill suggestions and an optional trend matcher | Gemini API Terms |

> No model was fine-tuned or self-trained. By default the trend matcher uses MiniLM and moves to Gemini embeddings only after a passing method-equivalence report. The default runtime uses no language model.

### 4.2 Datasets

List all datasets used for training, fine-tuning, evaluation, or in the running application. State clearly if a dataset contains personal or sensitive data.

| Dataset Name | Source / URL | Type (public / private / self-collected / synthetic) | License | Personal Data? (Y/N) |
|---|---|---|---|---|
| 142 skills, 48 roles (33 target) and role requirements | Team curation; O*NET 31.0 ([onetcenter.org](https://www.onetcenter.org/)) | Public-derived, curated | O*NET CC BY 4.0, with stated exceptions | N |
| arXiv cs.AI paper metadata and mention counts | [arxiv.org](https://arxiv.org/) | Public | Metadata CC0 1.0; papers keep own licences | Y: public author names only |
| U.S. occupational projections 2023-2033 | [bls.gov](https://www.bls.gov/emp/) | Public, derived | U.S. public domain; not a Malaysian forecast | N |
| October 2024 trend replay and synthetic fallback | Team-created from dated arXiv metadata | Public-derived, synthetic | Team-created; labelled on screen | N |
| 17 SDG goals, 169 targets; 88 role and 167 skill alignment rows | [UN SDG API](https://unstats.un.org/SDGAPI/v1/sdg/Goal/List); team curation | Public, curated | UN terms; no UN endorsement | N |
| 104 courses and skill prerequisites | Microsoft Learn; Coursera; named providers | Public facts, curated | Rights remain with providers | N |
| 1,175 job postings; 14 certifications; exchange rates | Job boards above; certification issuers; [BNM](https://api.bnm.gov.my/) | Public, curated | Each source's terms | N: employers named only |
| Monthly Labour Force Survey; MyCOL 2024/2025 | [OpenDOSM](https://open.dosm.gov.my/data-catalogue/lfs_month); TalentCorp | Public aggregates, crosswalk | CC BY 4.0; TalentCorp terms | N |
| Demonstration profiles, employers, CVs and fixtures | Team-created | Synthetic | Team-created | N |

### 4.3 AI-Assisted Development Tools

Tools used to help write code, design, content, or documentation (e.g., chat assistants, code completion tools, image generators). Declaring these tools does not reduce your score; undeclared use may.

Did your team use any generative-AI tool to help create code, design, text, or other project material?

☑ Yes ☐ No

If yes, list them below:

| Tool & Version | Used For | Extent of Use (minor / moderate / major) |
|---|---|---|
| Anthropic Claude Code; versions varied | Code, debugging, documentation, submission drafting, pitch deck and demo-film composition | Major |
| OpenAI Codex; versions varied | Debugging, implementation review, code and document corrections | Major |
| Greptile; version not recorded | Automated pull-request review comments | Moderate |
| Replit Agent; version not recorded | Deployment configuration, publishing and repository exploration | Minor |
| Google Antigravity agent; version not recorded | Repository exploration | Minor |
| ElevenLabs; stock voice, no cloning | Demo-film narration only; not part of the application | Minor |

> Non-generative presentation tools: Remotion 4.0.538 for demo-film composition, Mixkit for media assets, and Google Fonts for typefaces.

Briefly describe how your team reviewed, tested, and took responsibility for AI-generated output:

[Maximum 100 words]

<!-- answer:start technical-4.3 limit=100 -->
> The team set Adept's product direction and reviewed changes through pull requests before merging. Claude Code produced much of the source and document drafts, and Codex helped debug and review. Team members remain responsible for all accepted code and claims. Changes must pass automated lint, type, contract, attribution and fairness checks, and factual claims are checked against source records and dates. Model output cannot create catalogue entries or personnel decisions.
<!-- answer:end technical-4.3 -->

## 5. Sponsor-Provided Resources

Declare any official SDC sponsor-provided GenAI API, cloud credits, tools, mentoring, or data that your team used.

Did your project use any official SDC sponsor-provided resource?

☑ Yes ☐ No

If yes, list them below:

| Sponsor | Resource (API / credits / platform / data) | How It Was Used in the Project |
|---|---|---|
| Replit | Core subscription, Autoscale deployment, managed PostgreSQL | Public prototype, private API and persistent application records; Replit Agent is declared in Section 4.3 |
| RunPod | US$25 credits; GPU Pod test; Serverless MiniLM and GLM-5.3 endpoints | Research embeddings and optional Adi inference; the one-off Pod test validated batch encoding |

Was the sponsor resource essential to the core functionality of the prototype, or could it be replaced? Explain briefly:

[Maximum 100 words]

<!-- answer:start technical-5 limit=100 -->
> Both are important to the current deployment and both can be replaced. Replit hosts the web server, API and database; moving would mean migrating the same schema, sessions and backups to another host. RunPod provides MiniLM encoding and optional Adi inference; replacing MiniLM needs a method-equivalence check before any scored series changes. Matching and plan reads are deterministic and make no per-page model call, and provider outages keep dated data or show an unavailable state, so the core journey continues without either model service.
<!-- answer:end technical-5 -->

## 6. Security, Privacy & Responsible Use

### 6.1 Data Handling & Privacy

What user or personal data does your application collect, store, or send to third-party services (including AI APIs)? How is it protected, and how long is it kept? State “No user data is collected” if applicable.

[Maximum 150 words]

<!-- answer:start technical-6.1 limit=150 -->
> The demonstration uses synthetic identities and CVs. Signed accounts can store names, emails, password hashes, confirmed skills, preferences, memberships, plans, progress and evidence links in PostgreSQL. CV files are parsed in memory and not retained. Members opt in to share skills and progress, and personal plans and assistant conversations stay separate. Authentication, server-side membership checks, upload limits and HTTP-only signed cookies protect this data.

> Optional Gemini suggestions receive short phrases with contact details removed. Optional Adi providers receive filtered context and server-written candidate answers; redaction reduces but cannot eliminate the chance of personal information leaving the service. MiniLM receives only public research and catalogue text.

> Data is kept until the user deletes the account, and account export and deletion are built in. Automatic retention schedules and backup-erasure testing are not yet in place, and Adept makes no PDPA certification claim.
<!-- answer:end technical-6.1 -->

### 6.2 Known Limitations & Risks

Identify the main technical limitations of your AI components (e.g., hallucination, bias, rate limits, dependency on a single provider) and any mitigation you have implemented.

[Maximum 150 words]

<!-- answer:start technical-6.2 limit=150 -->
> **Hallucination.** Adi can only select server-written answers; validation rejects unknown IDs, and a fixed guide takes over on failure. An answer can still be selected for the wrong question, so people keep the final decision.

> **Signal quality.** arXiv attention and a U.S. labour baseline cannot measure Malaysian occupation demand. Scenarios and exposure values are heuristics, not calibrated probabilities. Adept labels them as estimates and shows source dates and fallbacks.

> **Bias.** Scores read only skills, trend and interest. Counterfactual tests found no rank change in 75 swaps, but this does not prove universal fairness.

> **Coverage.** The catalogue covers selected roles and courses, and only 38% of openings map to them today. Fees and openings change.

> **Provider dependency.** Hosting and encoding rely on Replit and RunPod, with Gemini failover for Adi. Rate limits and bounded requests limit runaway use. Production refresh still needs confirmation.
<!-- answer:end technical-6.2 -->

[[break]]

## 7. Compliance & Readiness Checklist

Tick all boxes that apply before submitting.

☑ All APIs, cloud services, AI tools, models, and datasets used in the project are declared in this document.

☐ All third-party code, datasets, and models are used in accordance with their licenses, and attribution is provided where required.

☐ No API keys, passwords, or other credentials are exposed in the code repository, prototype, or this document.

☑ Any use of generative-AI tools for development has been disclosed and reviewed by the team.

☑ Any use of official SDC sponsor resources has been declared in Section 5.

☐ The prototype described here is accessible to judges through the links provided in Section 1.

☐ All fields in this template have been completed within the word limits stated.

## 8. Declaration

By submitting this document, the team leader confirms that the information provided is complete and accurate to the best of the team’s knowledge, and that every API, cloud service, AI tool, dataset, model, and sponsor resource used in the project has been declared.

[Signature]

[Date]

[[break]]

## Appendix: System Block Diagram

[[diagram]]
