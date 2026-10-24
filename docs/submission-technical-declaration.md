# Adept: technical tools declaration

Draft prepared on 22 October 2026 against the supplied **SDC Hackathon Technical Tools
Declaration Template**. Its deadline field is unspecified; confirm it with the organisers.
This document records repository evidence and explicit unknowns, not a signed compliance claim.
Personal contact details belong in the private submission PDF, not in this public repository.

Updated 24 October 2026 for the root-only, single-public-server source revision, current dependency locks, live-data connectors and separate AI services. A source pin is not a claim about the inventory of an older deployed image.

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

**Diagram appendix:** [current system block diagram](submission-proposal.md#31-conceptual-tech-stack),
[full Mermaid collection](../README.md#diagrams), and the
[offline pan-and-zoom viewer](diagrams/index.html). Diagram relationships are traced to routers,
the root launcher, Next.js routes, FastAPI routers and migrations. Schema excerpts distinguish enforced foreign keys from logical joins.

### 2.2 Languages, frameworks and libraries

Versions below describe the reviewed source/lockfiles, not every deployed environment.
The authoritative inputs are [web package](../src/web/package.json), [pnpm lock](../pnpm-lock.yaml),
[Python project](../pyproject.toml), [uv lock](../uv.lock), and
[worker requirements](../src/pipelines/trends/runpod/requirements.txt). Runtime fallback
requirements remain in [requirements.txt](../requirements.txt). Full transitive notices must
be retained with distribution.

| Name and version / constraint | Licence | Purpose |
|---|---|---|
| Python 3.11; Node.js 24; pnpm 10.29.3 | PSF; MIT; MIT | Root supervisor, API/pipelines, standalone web and package manager. |
| Next.js / eslint-config-next 16.4.2; React / React DOM 19.2.9 | MIT | Server-rendered product, route handlers, API proxy and UI. |
| TypeScript 5.9.3 | Apache-2.0 | Strict web typing. |
| Tailwind CSS / PostCSS plugin 4.1.18; next-intl 4.14.9 | MIT | Styling; English, Bahasa Melayu and Chinese. |
| Three.js 0.180.0 | MIT | On-demand 3D Adi mascot. |
| lucide-react ^1.61.0 | ISC | Icons. |
| class-variance-authority 0.7.1; clsx 2.1.1; tailwind-merge 3.3.1 | Apache-2.0; MIT; MIT | Component variants and class composition. |
| @fontsource-variable/inter ^5.3.0 | MIT package; SIL OFL 1.1 font | Installed font dependency; current product CSS uses Arial/system fonts. |
| openapi-fetch 0.14.1; openapi-typescript 7.9.1 | MIT | Typed private API client and generated contracts. |
| @types/node 22.20.5; @types/react 19.2.18; @types/react-dom 19.2.7; @types/three 0.180.0 | MIT | Development type declarations; not the runtime Node version. |
| FastAPI 0.161.1; Pydantic 2.14.1; pydantic-settings 2.16.1 | MIT | API, contracts and configuration; resolved uv-lock versions. |
| Uvicorn 0.54.0, standard extras | BSD-3-Clause | Private ASGI server; loopback binding. |
| psycopg 3.3.6; psycopg-pool 3.3.3 | LGPL-3.0-only; bundled binaries have additional notices | PostgreSQL access, pooling and stale-session recovery. |
| python-multipart 0.0.32; PyJWT 2.15.1 | Apache-2.0; MIT | Upload parsing and optional Supabase JWT verification. |
| PyMuPDF 1.28.2 (source constraint <2) | AGPL-3.0 or commercial | In-memory PDF text extraction; review distribution obligations. DOCX/text handling also uses standard-library parsing. |
| PostgreSQL 16; pgvector | PostgreSQL License | Durable relational storage and embedding indexes; extension version is deployment-dependent. |
| sentence-transformers 6.2.0; transformers 5.20.2; torch 2.14.1 | Apache-2.0; Apache-2.0; BSD-3-Clause | Hardened worker source pins; require an image rebuild before they describe the live worker. |
| runpod 1.12.0; worker httpx 0.28.1 | MIT; BSD-3-Clause | Queue worker SDK and HTTP transport. [SDK licence](https://github.com/runpod/runpod-python/blob/main/LICENSE). |
| pytest 9.1.1; API httpx 0.28.1; Ruff 0.17.2; ESLint 9.39.5 | MIT; BSD-3-Clause; MIT; MIT | Regression tests, HTTP client and quality gates. |
| PyYAML 6.0.3; actionlint 1.7.7 | MIT | Workflow parsing and publication-policy validation. |
| uv; Prettier ^3.9.10 | MIT/Apache-2.0; MIT | Environment/lock tooling and formatting; uv tool version is environment-dependent. |
| Mermaid 11.12.0; Playwright renderer | MIT; Apache-2.0 | Documentation-only SVG generation; exported diagram viewer works offline. |

The Express/Drizzle/generated-client/mockup artifact scaffold has been removed from this
source revision. It is not part of Adept's product stack. Framework code remains Next.js;
this is not a conversion to Vite or a static SPA.

Docker Desktop/Engine and Compose are local development tools under their applicable Docker
distribution terms; they are not a cloud host. This draft does not assert that every transitive
licence obligation has been discharged. Review [PyMuPDF's licensing statement](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)
and upstream notices before signing the final compliance checklist. Adept's own repository
licence is [Apache-2.0](../LICENSE); that does not replace dependency licences.

## 3. APIs and cloud services

### 3.1 External APIs

| API and provider | Access tier | Purpose and invocation |
|---|---|---|
| [arXiv cs.AI RSS](https://rss.arxiv.org/rss/cs.AI) | Public/free feed; provider rate limits and terms apply | Offline research-attention ingestion; no arXiv call on a recommendation request. The implemented ingest uses RSS, not the search API. |
| [UN Statistics SDG API](https://unstats.un.org/SDGAPI/v1/sdg/Goal/List) | Public/free | Goal and target sync; scheduled source audit and protected admin sync. |
| [Microsoft Learn Catalog API](https://learn.microsoft.com/en-us/training/support/catalog-api) | Public/free | Curated course/module metadata, catalogue sync and availability checks. |
| [Coursera courses API](https://api.coursera.org/api/courses.v1) | Public endpoint used by code; provider terms and availability apply | Curated slug/workload availability checks; no paid subscription or sponsorship inferred. |
| [Bank Negara Malaysia OpenAPI](https://api.bnm.gov.my/) | Public/free endpoint | Exchange rates for foreign-currency course price estimates. |
| Cited course and evidence provider HTTPS pages | Public page access; not a single API | Course facts, link audits and provider certificate-page reachability checks. |
| RunPod / Google Gemini chat | Server keys; provider terms/usage charges | Adi primary: `glm-5.3` at `https://api.runpod.ai/v2/b1dd8hy2hqo1nb/openai/v1`. Gemini failover models configured as `gemini-3.5-flash-lite,gemini-3.6-flash,gemini-3.1-flash-lite`; availability is provider-dependent. |
| RunPod MiniLM | Dedicated `TRENDS_RUNPOD_API_KEY`; usage charges | `https://api.runpod.ai/v2/ta14jd0by2ijl2`: POST `/runsync`, or POST `/run` then GET `/status/{job_id}`; GET `/health`. Public research/catalogue embeddings, separate from Adi. |
| Google Gemini embedding API | Optional `GEMINI_API_KEY`; provider terms/charges | `gemini-embedding-001` through batchEmbedContents; 768-dimensional, normalised catalogue/short-phrase embeddings for CV skill suggestions. Enabled only by configuration and an existing catalogue index. |
| Employer and remote-job feeds | Public connectors; terms, robots rules and availability apply | Greenhouse, Lever, Ashby, Workday and Jibe career feeds; Himalayas, Jobicy, Remote OK and Remotive. Malaysia/eligible-remote filtering, source attribution and unchanged apply links. |
| Careerjet / Jooble / web3.career | Optional publisher/API keys | Additional job connectors run only when their respective keys are configured; no blanket claim that every connector is active. |

The BLS baseline is committed data, not an external API called by the running recommendation
service. Pinned MiniLM weights are downloaded from Hugging Face while building the worker
image; inference is hosted on RunPod. The worker loads weights offline at runtime. Do not
include API keys in this document.

### 3.2 Cloud platforms and deployment

| Service and provider | Plan / region | Purpose and verified status |
|---|---|---|
| GitHub repository / Actions | Account plan and runner region not verified; workflows use `ubuntu-latest` | Quality CI, source audit, GHCR worker publication and conditional trend refresh. The image publisher succeeded; the first real refresh failed saving to private database host `helium`. |
| Local Docker Compose | Local development; no cloud region | PostgreSQL/pgvector only; web/API use root commands, not three app containers. |
| Replit Autoscale | Partner-managed account; plan/region unverified | Selected public host. Pages and API/database health were reachable on 24 October 2026. The proposed root deployment exposes one Next.js port with private FastAPI; verify the published source revision separately. |
| Supabase PostgreSQL / Auth | Optional alternate integration; not the observed public auth mode | JWT-verification path exists. Observed health reports `auth_mode=demo`, the legacy name for normal local PostgreSQL accounts; production disables fixture/default users. |
| RunPod | GLM endpoint and deployed MiniLM worker; plan/region/credits unverified | Historical GLM request and MiniLM 384-dimensional inference were verified. Hardened worker source pins still require rebuild/redeploy; no successful new snapshot publication is claimed. |
| Other storage / analytics / services used by teammates | Team confirmation required | Add actual services used outside the repository before signing. |

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
[scoring](../src/pipelines/trends/score.py), [publication](../src/pipelines/trends/run.py),
and [exposure methodology](skill-exposure-methodology.md).

### 4.2 Datasets

Counts below describe committed seed files inspected on 24 October 2026 (job rows last seen 23 October), not the contents
of every deployed database. No model was fine-tuned on these fixtures.

| Dataset name | Source / URL | Type | Personal data? | Licence / terms and use |
|---|---|---|---|---|
| Custom skill and role catalogue: 140 skills, 31 roles (28 targets) | [Taxonomy seed](../src/data/seed/taxonomy/) | Team-curated / synthetic catalogue | No | Team curation; upstream source references retained where supplied. Not a complete official ESCO/O*NET import. Used for extraction and matching. |
| arXiv cs.AI research signal | [Ingest](../src/pipelines/trends/arxiv_ingest.py), [arXiv terms](https://info.arxiv.org/help/api/tou.html) | Public | No learner data; raw feed metadata may contain public author names | Provider terms and per-article licences apply; avoid a blanket CC0 claim. Research text is used offline for aggregated skill signals. |
| BLS 2023–2033-derived labour baseline | [Committed baseline](../src/data/seed/labor_decay.csv), [BLS source](https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm) | Public / team-derived | No | US government source with attribution; occupation-to-skill mapping is a team method. The linked live BLS table can advance to newer editions. |
| Canonical skill exposure and historical snapshots | [Seed data](../src/data/seed/), [methodology](skill-exposure-methodology.md) | Curated / public-derived | No | Reviewer-assigned exposure scores and dated replay fixtures; not measured probabilities. October 2026-labelled demo snapshots replay October 2024 research windows, disclosed in provenance. |
| 17 SDG goals and 169 targets | [UN API](https://unstats.un.org/SDGAPI/v1/sdg/Goal/List), [seed](../src/data/seed/sdg/) | Public | No | UN data terms and attribution; official target wording retained. |
| 61 role-target and 165 skill-target links | [Mapping seed](../src/data/seed/sdg/), cited evidence per record | Team-curated | No | Draft team interpretations with reasons and evidence; not official UN endorsements. Human review status is explicit. |
| 98 course records | [Catalogue sources](../src/api/app/features/pathway/catalogue_sources.py), [seed](../src/data/seed/courses/) | Public facts / curated | No | Microsoft, Coursera, local providers and universities retain their respective terms. Prices and HRD Corp notes are dated estimates, not entitlement guarantees. |
| 1,210 public job-posting records | [Job pipeline/connectors](../src/pipelines/jobs/), [dated seed](../src/data/seed/jobs/job_postings.csv) | Public facts | No learner profiles; employer contacts may exist in source material | Stored title/location/apply URL, catalogue skills and dates; full ad text is processed in memory. Counts are a dated seed inventory, not a guarantee of currently open vacancies. |
| 14 certification exams | [Certification catalogue](../src/data/seed/jobs/certifications.csv), cited issuer pages | Curated public facts | No | Official issuer terms/fees and retrieval dates; estimated MYR conversion, no payment processing or certification guarantee. |
| Exchange rates | [BNM OpenAPI](https://api.bnm.gov.my/) | Public | No | BNM terms and attribution; used for estimated MYR costs. |
| Five selected demo CVs and complete intake profiles | [Demo CVs and profile guide](../submission/demo-cvs/) | Synthetic | No real identities | Imran Hakim, Sofia Tan, Meera Anand, Adrian Lim and Nur Hana. Supplied fictional CVs; additional intake values are editable demo assumptions, not extracted or verified qualifications. |
| Regression personas, organisation members and CV fixtures | [Fixtures](../tests/api/profile/fixtures/cvs/), [persona seed](../src/data/seed/personas/), [organisation seed](../src/data/seed/org/) | Synthetic | No real identities | Automated regression and seed data, distinct from the five selected presentation CVs. Local sign-up must use invented details. |

### 4.3 AI-assisted development tools

**Yes.** The team defined Adept's problem, product direction and SDG focus, and used AI tools
for development support, debugging, presentation work and review. The following usage was
confirmed by the team leader on 25 October 2026. Exact tool/model versions were not recorded;
do not infer them from installed software or repository context files.

| Tool and version | Extent of use | Used for |
|---|---|---|
| OpenAI Codex | Major debugging and review support | Repository inspection, debugging, resolving Greptile findings, code/configuration corrections, checks and documentation review. |
| Anthropic Claude Code | Major demo/presentation support | Demo-video creation and pitch-deck design concepts, layout and presentation material. |
| Replit Agent | Minor repository exploration | Exploring the repository and understanding its structure. |
| Google Antigravity agent | Minor repository exploration | Exploring the repository and understanding its structure. |
| Greptile | Moderate automated review support | Reviewing pull requests and identifying issues for the team to assess and resolve. |

Open-source skills/plugins and connected-app integrations extended the team's authoring and
inspection workflows. Declare the actual packages/repositories and relevant external services
used, with their applicable terms; installing a tool does not establish that every capability
or connected service was used. These extensions are development tools, not additional models
embedded in Adept. The team retains responsibility for the submitted product and materials.

**Review and responsibility (maximum 100 words):**

<!-- answer:start technical-4.3 limit=100 -->
The team chose Adept's problem, product direction and SDG focus. AI tools supported debugging,
repository exploration, demo-video production, pitch design and automated review. Team members
assessed suggestions, made corrections and retained final decisions. Technical claims are
checked against source, dependency records, datasets and test results. AI-generated material
requires human review; passing tests does not prove universal fairness, legal compliance or
employment outcomes. The leader reviews the final documents, confirms actual tool and sponsor
usage, and takes responsibility for the submission.

<!-- answer:end technical-4.3 -->

## 5. Sponsor-provided resources

**API usage: yes, Runpod.** Local configuration and a small verified request establish
hosted inference usage. Sponsor-provided credit entitlement, workshop attendance and
mentoring remain for the team to confirm.

| Sponsor | Resource | How used |
|---|---|---|
| Runpod | GLM-5.3 endpoint and MiniLM Serverless worker | Adi primary and public research/catalogue embeddings; live inference verified separately. Credit entitlement remains unverified. |

**Essential or replaceable (maximum 100 words):**

<!-- answer:start technical-5 limit=100 -->
RunPod supplies Adi's configured GLM-5.3 endpoint and hosts the pinned MiniLM research encoder.
Gemini and a built-in guide provide assistant fallback; optional Gemini embeddings support
catalogue skill suggestions. MiniLM also has an explicit local CPU development backend.
Role scoring, pathway ordering and SDG calculations remain deterministic. Web/database hosting,
worker inference and validated snapshot publication are separate checks. Historical inference
passed, but newer worker dependencies require rebuild/redeploy and a successful trend publish
must be verified. Sponsor credits, mentoring and workshop participation require team confirmation.

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

[Compose](../docker-compose.yml) · [requirements](../requirements.txt) ·
[web manifest](../src/web/package.json) · [auth](../src/api/app/core/auth.py) ·
[LLM providers and failover](../src/api/app/core/llm/provider.py) ·
[trend workflow](../.github/workflows/trends-refresh.yml) ·
[source audit](../.github/workflows/data-sources.yml) ·
[catalogue sources](../src/api/app/features/pathway/catalogue_sources.py).
