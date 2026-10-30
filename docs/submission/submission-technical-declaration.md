# Adept: technical tools declaration

Updated 30 October 2026 against the supplied finalist **Technical & Tools Declaration**
template. Its stated deadline is **1 November 2026**. Sections 1-8 follow that template.
This document records repository evidence and explicit unknowns, not a signed compliance claim.
Personal contact details belong in the private submission PDF, not in this public repository.

Updated 30 October 2026 for the root-only, single-public-server source revision, current dependency locks, live-data connectors and separate AI services. A source pin is not a claim about the inventory of an older deployed image.

## 1. Team and project overview

| Template field | Response |
|---|---|
| Team name | Pecel Lele (repository team record; confirm registration spelling). |
| Project / solution name | Adept. |
| Name (leader) | Team to complete privately in the submission PDF. |
| Email and phone (leader) | Team to complete privately in the submission PDF. |
| University affiliation(s) | Xiamen University Malaysia, per the project README. |
| Live prototype URL | [adept-my.replit.app](https://adept-my.replit.app): public pages and API/database health returned 200 on 24 October 2026. The deployed commit and the success of a newer publish attempt remain unverified. Local development uses :3000 and private API docs :8000/docs. |
| Code repository URL | [pecel-lelele/adept](https://github.com/pecel-lelele/adept); public visibility verified; confirm access again before submission. |

## 2. Architecture and technology stack

### 2.1 System architecture overview

<!-- answer:start technical-2.1 limit=200 -->
Adept keeps product source under root src/, tests under tests/, and documentation and
submission material at their required root paths. One public Next.js standalone server
renders pages, runs server actions and forwards API requests to private FastAPI on loopback.
The root Python launcher checks configuration and API/database readiness, supervises both
children, and performs no startup migrations or seeding. HTTP-only signed cookies hold local
account sessions; PostgreSQL stores profiles, memberships, plans, evidence and catalogue data.

The batch research pipeline calls a pinned 384-dimensional MiniLM encoder on RunPod and
validates dated trend snapshots before atomic publication. Optional 768-dimensional Gemini
embeddings map unfamiliar skill phrases to catalogue suggestions. Matching and pathways use
deterministic rules. Adi can use GLM-5.3 with Gemini failover to select validated answer-block
IDs; displayed wording comes from server-authored facts.

Public employer/remote-job feeds, sourced courses, certification fees, official UN SDGs and
BNM exchange rates complement research signals. GitHub Actions runs quality checks, database
recovery tests, the actual root deployment smoke, weekly source audits and conditional trend
refresh. Local Compose provides PostgreSQL only. The public site's reachability and MiniLM
inference were observed separately; latest-source deployment and successful new snapshot
publication require their own verification.

<!-- answer:end technical-2.1 -->

**Diagram appendix:** [current system block diagram](submission-proposal.md#31-final-system-architecture),
[full Mermaid collection](../../README.md#diagrams), and the
[offline pan-and-zoom viewer](../diagrams/index.html). Diagram relationships are traced to routers,
the root launcher, Next.js routes, FastAPI routers and migrations. Schema excerpts distinguish enforced foreign keys from logical joins.

### 2.2 Languages, frameworks and libraries

Versions below describe the reviewed source/lockfiles, not every deployed environment.
The authoritative inputs are [web package](../../src/web/package.json), [pnpm lock](../../pnpm-lock.yaml),
[Python project](../../pyproject.toml), [uv lock](../../uv.lock), and
[worker requirements](../../src/pipelines/trends/runpod/requirements.txt). Runtime fallback
requirements remain in [requirements.txt](../../requirements.txt). Full transitive notices must
be retained with distribution.

| Name & Version | Purpose in Project | License |
|---|---|---|
| Python >=3.11 (deployment runtime 3.11) | API, pipelines and root supervisor | Python Software Foundation License |
| Node.js 24; pnpm 10.29.3 | Next.js runtime and package management | MIT |
| Next.js 16.4.2; React and React DOM 19.2.9 | Server rendering, routing, UI and same-origin API proxy | MIT |
| TypeScript ~5.9.3 | Strict typing | Apache-2.0 |
| Tailwind CSS / @tailwindcss/postcss 4.1.18 | Styling | MIT |
| next-intl 4.14.9 | English, Bahasa Melayu and Chinese | MIT |
| Three.js 0.180.0 | Adi's interactive 3D mascot | MIT |
| lucide-react ^1.61.0 | Interface icons | ISC |
| class-variance-authority 0.7.1 | Component variants | Apache-2.0 |
| clsx 2.1.1; tailwind-merge 3.3.1 | CSS class composition | MIT |
| Google Fonts: Inter via @fontsource-variable/inter ^5.3.0 | Installed Inter font assets; current global UI styling uses system Arial, not a live Google Fonts request | MIT package; SIL OFL 1.1 font |
| openapi-fetch 0.14.1; openapi-typescript 7.9.1 | Typed API client and generated contracts | MIT |
| @types/node 22.20.5; @types/react 19.2.18; @types/react-dom 19.2.7; @types/three 0.180.0 | Development type definitions | MIT |
| FastAPI >=0.161.1 | HTTP API and OpenAPI | MIT |
| Pydantic >=2.7,<3; pydantic-settings >=2.16.1 | Contracts and configuration | MIT |
| Uvicorn >=0.54.0 | Private ASGI service | BSD-3-Clause |
| psycopg[binary] >=3.3.6; psycopg-pool >=3.3.3 | PostgreSQL access and pooling | LGPL-3.0-only; bundled binary components have additional notices |
| python-multipart >=0.0.32 | Multipart CV uploads | Apache-2.0 |
| Python standard library | Signed local sessions and scrypt password hashing | PSF-2.0 |
| PyMuPDF >=1.24.0,<2 | In-memory PDF text extraction; review distribution obligations before release | AGPL-3.0 or Artifex commercial licence |
| HTTPX >=0.28.1 | External API and model-provider requests; worker pins 0.28.1 | BSD-3-Clause |
| PostgreSQL 16; pgvector (pgvector/pgvector:pg16; extension version not pinned) | Relational storage; separate 384-dimensional MiniLM and 768-dimensional Gemini indexes | PostgreSQL License |
| sentence-transformers 6.2.0; Transformers 5.20.2; RunPod Python SDK 1.12.0 | Pinned MiniLM Serverless worker source; deployed image versions require separate verification | Apache-2.0 for Sentence Transformers/Transformers; MIT for RunPod SDK |
| PyTorch 2.14.1 | MiniLM worker source dependency | BSD-3-Clause |
| pytest >=9.1.1; Ruff >=0.17.2; ESLint 9.39.5; eslint-config-next 16.4.2 | Tests, quality checks and linting | MIT |
| uv | Python environment tooling; version is environment-dependent | MIT or Apache-2.0 |
| Mermaid 11.12.0 | Documentation-only diagram generation | MIT |
| PyYAML 6.0.3; actionlint 1.7.7 | Workflow parsing and publication-policy validation | MIT |
| Prettier ^3.9.10 | Development formatting | MIT |
| Playwright renderer | Documentation-only diagram rendering | Apache-2.0 |

The Express/Drizzle/generated-client/mockup artifact scaffold has been removed from this
source revision. It is not part of Adept's product stack. Framework code remains Next.js;
this is not a conversion to Vite or a static SPA.

Docker Desktop/Engine and Compose are local development tools under their applicable Docker
distribution terms; they are not a cloud host. This draft does not assert that every transitive
licence obligation has been discharged. Review [PyMuPDF's licensing statement](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)
and upstream notices before signing the final compliance checklist. Adept's own repository
licence is [Apache-2.0](../../LICENSE); that does not replace dependency licences.

## 3. APIs and cloud services

### 3.1 External APIs

| API & Provider | Purpose in Project | Access Tier (free / paid / sponsor-provided) |
|---|---|---|
| [arXiv cs.AI RSS](https://rss.arxiv.org/rss/cs.AI) | Offline research-attention ingestion; historical replay windows also cite the query API. Current ingest uses RSS; no arXiv call on a recommendation request. | Public/free; rate limits and terms apply |
| [UN Statistics SDG Goal and Target APIs](https://unstats.un.org/SDGAPI/v1/sdg/Goal/List) | Goal and target sync; scheduled source audit | Public/free |
| [Microsoft Learn Catalog API](https://learn.microsoft.com/en-us/training/support/catalog-api) and exam-pricing page | Course/module metadata, catalogue sync, availability checks and certification prices | Public/free |
| [Coursera courses API](https://api.coursera.org/api/courses.v1) | Curated slug/workload availability checks; no subscription or sponsorship inferred | Public endpoint; provider terms apply |
| [Bank Negara Malaysia OpenAPI](https://api.bnm.gov.my/) | Exchange rates for MYR price estimates | Public/free |
| Public job-posting feeds: Greenhouse, Lever, Ashby, Workday, Jibe, Himalayas, Jobicy, Remote OK, Remotive | Dated vacancy and skill evidence; these nine source families occur in the committed 23 October extract. SmartRecruiters is excluded from configured sources. | Public access; each source's terms apply |
| Optional keyed job APIs: Careerjet, Jooble, Web3.career | Connectors exist but are skipped in the committed fetch log; run only when configured | Authenticated; provider terms and credentials required |
| Cited provider HTTPS pages (courses, certifications) | Course facts, link audits and certification-page reachability | Public page access; not a single API |
| RunPod: GLM-5.3 for Adi; Serverless MiniLM batch embeddings | Separate endpoints and credentials: Adi selects validated answer blocks; MiniLM generates offline 384-dimensional research/catalogue vectors | Server API keys; sponsor resource usage declared in section 5; provider terms and charges apply |
| Google Gemini API (3.5 Flash Lite, 3.6 Flash, 3.1 Flash Lite; Embedding 001) | Optional Adi failover in that order; optional 768-dimensional skill suggestions using redacted short phrases and an existing catalogue index | Server API key; optional provider integrations; configured failover requires credentials, not a blanket production-disabled claim |

The BLS baseline is committed data, not an external API called by the running recommendation
service. Pinned MiniLM weights are downloaded from Hugging Face while building the worker
image; inference is hosted on RunPod. The worker loads weights offline at runtime. Do not
include API keys in this document.

### 3.2 Cloud platforms and deployment

| Service & Provider | Purpose in Project | Plan / Region |
|---|---|---|
| GitHub repository / Actions | Version control, quality CI, source audit, worker publication and conditional trend refresh. The first real refresh failed saving to private database host `helium`. | Public repository; GitHub-hosted Linux runners (`ubuntu-latest`) |
| Local Docker Compose | PostgreSQL/pgvector only; web/API run through root commands | Local Windows Docker Desktop; no cloud region |
| Replit Autoscale | Hosts the deployed public prototype at `https://adept-my.replit.app`; landing, About and API/database health returned 200 on 25 October. One public Next.js server, private FastAPI; health does not identify the Git revision. | Sponsor-provided Replit Core subscription; Autoscale publishing |
| Replit integrated PostgreSQL | Managed application database for profiles, catalogue, snapshots, plans, progress and organisations; development and production databases are separate | Replit's built-in managed PostgreSQL, attached to the Core project |
| RunPod Serverless / hosted inference | Deployed MiniLM worker for offline embeddings and separate GLM-5.3 endpoint for Adi. Successful inference does not establish successful new snapshot publication. | US$25 sponsor-provided credits; usage-based Serverless/inference |
| GitHub Container Registry (GHCR) | Stores/distributes the MiniLM worker container image | Public `ghcr.io/pecel-lelele/adept-minilm` image |

The Core subscription, US$25 credit allocation and use of Replit's integrated PostgreSQL were
confirmed by the team leader on 25 October 2026. Deployed authentication uses Adept's signed
local accounts stored in the same Replit database.
The Plan / Region column records confirmed plans/resources and does not infer physical
hosting location from the team's location. For deployment planning, Replit **Asia** is the
recommended geography for a Malaysian audience; RunPod's available-data-center scheduling
is recommended for this offline batch encoder. These are recommendations, not verified
active-region claims. See [Replit geography](https://docs.replit.com/features/publishing/project-geography),
[Replit database](https://docs.replit.com/features/database), and
[RunPod data-center settings](https://docs.runpod.io/serverless/endpoints/endpoint-configurations#data-centers).

Publishing needs the production database connection, stable session secret, shared proxy secret,
verified forwarding-hop count and exact origin. They are supplied in hosting secret/config
stores, never in the PDF. GitHub trend refresh separately needs `TREND_DATABASE_URL`,
`TRENDS_RUNPOD_API_KEY` and `TRENDS_RUNPOD_ENDPOINT_ID`. Its latest observed historical run
failed reaching the private development host `helium`; database preflight now rejects that
configuration before inference. A skipped/green job is not evidence of snapshot publication.


## 4. AI tools, models and datasets

### 4.1 AI models used in the solution

| Model and version | Source / provider | Licence / terms | Usage |
|---|---|---|---|
| [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Sentence Transformers weights hosted in the team's RunPod worker | Apache-2.0 | Pre-trained, no team fine-tuning. Pinned revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; 384-dimensional sentence/skill embeddings, cosine threshold 0.55. |
| GLM-5.3 | Runpod, model `glm-5.3` | Provider terms; team to review before signing | Grounded Adi assistance through an OpenAI-compatible endpoint; low reasoning and bounded output. Local request verified. |
| Gemini chat | Google; configured fallback list in section 3.1 | Provider terms | Adi failover, separate credentials; tested fallback behavior is not a claim of a current live request. |
| Gemini embedding-001 | Google Gemini REST API | Provider terms | Optional catalogue indexing/short skill-phrase suggestions, 768 dimensions. A separate purpose from MiniLM research embeddings; user confirmation required. |

**Six-stage trend pipeline:** arXiv RSS and committed BLS-derived data → strip HTML and split
abstracts → MiniLM sentence/skill vectors and per-week mention frequencies → log-ratio research
velocity blended 0.6/0.4 with the labour baseline, with scenario transformation → fresh-ingest,
distinct-period, minimum-coverage, known-ID and finite-value validation → atomic publication
of `trend_snapshots` and `trend_snapshot_meta`. A validation failure prevents new snapshot
publication; ingestion audit/raw data may already have been written.

This is a semantic encoder plus heuristics, not a trained predictor of actual job vacancies.
The fast-scenario range is not a calibrated statistical confidence interval. See
[scoring](../../src/pipelines/trends/score.py), [publication](../../src/pipelines/trends/run.py),
and [exposure methodology](../skill-exposure-methodology.md).

### 4.2 Datasets

Counts below describe committed seed files inspected on 24 October 2026 (job rows last seen 23 October), not the contents
of every deployed database. No model was fine-tuned on these fixtures.

| Dataset Name | Source / URL | Type (public / private / self-collected / synthetic) | License | Personal Data? (Y/N) |
|---|---|---|---|---|
| Custom skill and role catalogue (140 skills, 31 roles, 28 targets) | [Taxonomy seed](../../src/data/seed/taxonomy/) | Team-curated / synthetic | Team curation; upstream references retained; not a complete O*NET/ESCO import | No |
| O*NET 31.0 occupation crosswalk | [O*NET](https://www.onetcenter.org/), [curated provenance](../../src/data/seed/taxonomy/provenance.json) | Public-derived / curated | CC BY 4.0 with stated exceptions; credit and modifications required | No |
| arXiv cs.AI research signal | [RSS ingest](../../src/pipelines/trends/arxiv_ingest.py) and cached windows | Public | arXiv terms; metadata and paper content have different rights; no blanket CC0 claim | No learner data; raw feed metadata may contain public author names |
| BLS 2023–2033 labour baseline | [Committed extract](../../src/data/seed/labor_decay.csv), [BLS](https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm) | Public / team-derived | US government data, cite BLS; US baseline, not a Malaysian vacancy forecast | No |
| Canonical skill exposure and historical snapshots | [Seed data and fixtures](../../src/data/seed/), [methodology](../skill-exposure-methodology.md) | Curated / public-derived | Reviewer-assigned exposure estimates, not probabilities; demo snapshots replay October 2024 research windows | No |
| 17 SDG goals and 169 targets | [UN SDG API](https://unstats.un.org/SDGAPI/v1/sdg/Goal/List), [seed](../../src/data/seed/sdg/) | Public | UN data terms and attribution | No |
| 61 role-target and 165 skill-target links | [Mapping seed](../../src/data/seed/sdg/) | Team-curated | Draft team interpretations with cited evidence; no UN endorsement | No |
| Course records (98) and prerequisite graph | [Catalogue sources](../../src/api/app/features/pathway/catalogue_sources.py), [seed](../../src/data/seed/courses/) | Public facts / curated | Providers retain their terms; prices and HRD Corp notes are dated estimates | No |
| Job-posting extract (1,210 records, committed 23 October 2026) | [Public job boards and employer endpoints](../../src/data/seed/jobs/job_postings.csv) | Public / curated | Each board's terms; public access is not an open-data licence; counts do not guarantee current availability | No learner data; postings may name public employers |
| Certification and exam-pricing extract (14 exams) | [Microsoft, AWS, Google Cloud, IIBA and IAPP sources](../../src/data/seed/jobs/certifications.csv) | Public / curated | Issuer site terms; dated prices | No |
| Exchange rates | [BNM OpenAPI](https://api.bnm.gov.my/) | Public | BNM terms and attribution | No |
| Synthetic personas, organisations, regions and CVs | [Five selected demo CVs/profiles](../demo-cvs/), [regression fixtures](../../tests/api/profile/fixtures/cvs/), [seeds](../../src/data/seed/personas/) | Synthetic | Team-created evaluation/test data. Selected CVs: Imran, Sofia, Meera, Adrian and Nur Hana; additional intake settings are editable demo assumptions, not extracted qualifications. | No real identities |
| OpenDOSM monthly Labour Force Survey | [Official catalogue](https://open.dosm.gov.my/data-catalogue/lfs_month) | Public national aggregates | CC BY 4.0; retain DOSM attribution; monthly observation dates differ from retrieval dates | No |
| MyCOL 2024/2025 occupation groups and reviewed role crosswalk | [TalentCorp source and mapping evidence](../reference/critical-occupations.md) | Public-derived / curated | TalentCorp publication terms; no open-data licence inferred. 66 source groups, one reviewed stored role-ID mapping; historical badge only, no ranking effect | No |

### 4.3 AI-assisted development tools

**Yes.** The team defined Adept's problem, product direction and SDG focus. Claude Code was
the primary coding assistant and produced most of the application code, alongside its
demo-video and pitch-design work. Other AI tools supported debugging, exploration and review.
The following usage was
confirmed by the team leader on 25 October 2026. Exact tool/model versions were not recorded;
do not infer them from installed software or repository context files.

| Tool & Version | Used For | Extent of Use (minor / moderate / major) |
|---|---|---|
| OpenAI Codex; exact app/model version not recorded | Repository inspection, debugging, resolving Greptile findings, code/configuration corrections, checks and documentation review | Major debugging and review support |
| Anthropic Claude Code; exact app/model version not recorded | Produced most application code; also supported demo-video creation and pitch-deck design concepts, layout and presentation material | Major; primary implementation assistant |
| Replit Agent; exact version not recorded | Exploring the repository and understanding its structure | Minor |
| Google Antigravity agent; exact version not recorded | Exploring the repository and understanding its structure | Minor |
| Greptile; exact version not recorded | Reviewing pull requests and identifying issues for the team to assess and resolve | Moderate |

Open-source skills/plugins and connected-app integrations extended the team's authoring and
inspection workflows. Declare the actual packages/repositories and relevant external services
used, with their applicable terms; installing a tool does not establish that every capability
or connected service was used. These extensions are development tools, not additional models
embedded in Adept. The team retains responsibility for the submitted product and materials.

**Review and responsibility (maximum 100 words):**

<!-- answer:start technical-4.3 limit=100 -->
The team chose Adept's problem, product direction and SDG focus. Claude Code produced most
of the application code and supported the demo video and pitch design. Codex supported
debugging and corrections; other tools assisted exploration and PR review. Team members
assessed outputs and retained final decisions. Technical claims are
checked against source, dependency records, datasets and test results. AI-generated material
requires human review; passing tests does not prove universal fairness, legal compliance or
employment outcomes. The leader reviews the final documents, confirms actual tool and sponsor
usage, and takes responsibility for the submission.

<!-- answer:end technical-4.3 -->

### 4.4 Content and presentation tools

The team identified the following presentation tools on 30 October 2026.
This inventory does not establish the contents of a final exported video. Retain the final
asset credits and confirm which generated takes were used before signing this declaration.
These tools are used for presentation production, not career recommendations in Adept.

| Tool / version | Presentation purpose | Evidence and outstanding details |
|---|---|---|
| [Google Fonts](https://fonts.google.com/) | Presentation typography where used | Confirm the exact exported font families and retain their applicable font licence notices. |
| [Remotion](https://www.remotion.dev/) 4.0.538 | Motion graphics and demo-film composition | Version recorded by the team; the local video workspace is gitignored and not evidence of a reproducible application dependency. |
| [Mixkit](https://mixkit.co/license/) | Presentation media, music / sound effects as applicable | Record the exact downloaded asset pages and applicable item licences in final credits; these are not supplied in the tracked repository. |
| [ElevenLabs](https://elevenlabs.io/) | Demo/walkthrough video voiceover narration only (`submission/demo-video`) | The team confirmed use on 30 October 2026. Team recorded use strictly for demo video audio production with stock voice `21m00Tcm4TlvDq8ikWAM` (Rachel); no voice cloning; not integrated into or used by the Adept web application or recommendation runtime. |

The demo's statistical context and dates are listed in the
[demo evidence register](../demo-script.md#evidence-register). WEF forecasts are global estimates;
the Malaysian figure is a conditional ministerial warning, not observed job losses caused by AI.
MiniLM is already declared in section 4.1; public job feeds, BNM rates and the O*NET crosswalk
are declared in section 4.2. Workday career-site connectors use an undocumented public-facing
interface; public reachability does not establish an open-data licence or a stable API contract.

## 5. Sponsor-provided resources

**Yes: Replit deployment and RunPod inference/Serverless compute.** The team confirms using
Replit Core as the sponsor-provided subscription for deployment and the integrated PostgreSQL
database. The team received US$25 in RunPod sponsor credits and uses RunPod for the deployed
MiniLM Serverless worker and Adi's configured GLM-5.3 inference endpoint. These benefit details
are confirmed by the team leader; the [event site](https://sdchack.my/#sponsors) identifies
Replit and RunPod as supporters. No subscription duration or mentoring participation is inferred.

| Sponsor | Resource (API / credits / platform / data) | How It Was Used in the Project |
|---|---|---|
| RunPod | US$25 sponsor credits; GLM-5.3 inference endpoint and Serverless MiniLM worker | Adi's validated answer-block selection and offline public-research/catalogue embeddings. Worker inference succeeded; successful new trend-snapshot publication is a separate check. |
| Replit | Sponsor-provided Core subscription, cloud deployment and integrated PostgreSQL | Hosts the public Adept web/API and managed application database. Replit Agent was also used for repository exploration, as declared in section 4.3. |

**Essential or replaceable (maximum 100 words):**

<!-- answer:start technical-5 limit=100 -->
Replit hosts the deployed prototype and makes it accessible to judges. RunPod Serverless runs
the MiniLM research encoder, while a separate RunPod endpoint supplies Adi's GLM-5.3 inference.
These resources are important to the current deployment but replaceable: the web/API can move
to another compatible host, MiniLM has a local CPU backend, and Adi has Gemini failover and a
deterministic guide. Role matching and pathway generation use deterministic logic and saved
data rather than requiring generative inference for each recommendation. Successful worker
inference and successful publication of a new trend snapshot are separate checks.

<!-- answer:end technical-5 -->

## 6. Security, privacy and responsible use

### 6.1 Data handling and privacy

<!-- answer:start technical-6.1 limit=150 -->
The demonstration uses synthetic identities, organisations and CVs. PostgreSQL can store
account names/emails, scrypt password hashes, skills, preferences, memberships, learning
plans, progress and evidence links. CV files are parsed in memory and not retained; confirmed
skills are saved after review.

When enabled, Gemini receives short, contact-redacted skill phrases. Adi providers receive
sanitised conversation/context and candidate answer blocks; do not claim that all personalised
information stays local. MiniLM receives public research/catalogue text. PII filtering is a
mitigation, not a guarantee.

Signed sessions use HTTP-only cookies. Organisation workspaces constrain sharing. The public
proxy signs trusted visitor addresses; uploads/body sizes and rates are limited. Account
export and password-confirmed deletion exist, including a last-manager safeguard. No automatic
retention schedule or verified backup-erasure policy is implemented. Production requires
HTTPS, managed secrets and operational review. No real personal data enters the competition demo.

<!-- answer:end technical-6.1 -->

### 6.2 Known limitations and risks

<!-- answer:start technical-6.2 limit=150 -->
Research attention and US labour projections do not establish Malaysian vacancy forecasts.
Job feeds supply dated openings, not guaranteed availability or employment outcomes. Curated
catalogue coverage is limited; replay snapshots include historical observation windows.
Scenario/exposure values are heuristic estimates, not calibrated probabilities. SDG links are
team interpretations, not verified social impact.

CV parsing can miss aliases or scanned text; optional suggestions require confirmation.
Provider-page checks do not establish certificate ownership. Fees, eligibility and upstream
APIs change. Adi selects checked answer blocks, but relevance can still be wrong and human
judgment remains necessary. Validation, source metadata, deterministic fallbacks, counterfactual
checks, manual review and bounded network operations mitigate specific risks. Public reachability
and green CI do not establish a deployed commit, security certification, universal fairness or
improved employment outcomes.

<!-- answer:end technical-6.2 -->

## 7. Compliance and readiness

Final attestations remain unchecked until the team completes its review.

- [ ] Every service, development tool, model and dataset used by every member is declared.
- [ ] Dependency/data licences and required notices have been reviewed, including PyMuPDF.
- [ ] No credentials are exposed; final repository and deployment inspection completed.
- [ ] AI-assisted work has been disclosed and reviewed by the team.
- [ ] Sponsor resources, including mentoring/credits outside source control, are confirmed.
- [ ] Judges can access the public prototype and repository links in section 1.
- [ ] Team fields and all final template answers are complete within their word limits.

## 8. Declaration

**Unsigned draft.** The leader must review actual team usage and complete the supplied
accuracy declaration. A repository-generated draft cannot attest on the leader's behalf.

| Field | Completion |
|---|---|
| Signature | Leader to sign privately after review. |
| Date | Actual signing date. |
| Final filename | `SDC2026_<RegisteredTeamName>_TechDeclaration.pdf` |

## Implementation references

[Compose](../../docker-compose.yml) · [requirements](../../requirements.txt) ·
[web manifest](../../src/web/package.json) · [auth](../../src/api/app/core/auth.py) ·
[LLM providers and failover](../../src/api/app/core/llm/provider.py) ·
[trend workflow](../../.github/workflows/trends-refresh.yml) ·
[source audit](../../.github/workflows/data-sources.yml) ·
[catalogue sources](../../src/api/app/features/pathway/catalogue_sources.py).

## Final-round evidence update - 30 October 2026

The source declaration and this export distinguish runtime services from presentation
tools. RunPod hosts the pinned all-MiniLM-L6-v2 encoder and the separate GLM-5.3
endpoint; Gemini is the separately authenticated Adi failover. Replit hosts the
prototype and PostgreSQL. Google Fonts' Inter is distributed through the declared
Fontsource package; current app styling uses Arial/system fallbacks. ElevenLabs
was confirmed by the team as used, so it is declared as presentation
audio tooling, not an Adept runtime model. See section 4.4 for the team's stock-voice record; the synthesis model is unrecorded.

Human planning-time KPI: **0 testers, 0 measured human trials**, as confirmed by the
team on 30 October 2026. No achieved planning-time reduction is claimed. Automated
local API measurements are reported separately in `docs/evidence/kpi-automated-journeys.md`;
they exclude human review, browser interaction, network and a manual baseline.
This remains an unsigned draft, with private team fields reserved for completion.
