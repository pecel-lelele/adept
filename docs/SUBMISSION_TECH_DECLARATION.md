# Adept: technical tools declaration

Draft prepared on 22 October 2026 against the supplied **SDC Hackathon Technical Tools
Declaration Template**. Its deadline field is unspecified; confirm it with the organisers.
This document records repository evidence and explicit unknowns, not a signed compliance claim.
Personal contact details belong in the private submission PDF, not in this public repository.

## 1. Team and project overview

| Template field | Response |
|---|---|
| Team name | Team to confirm the exact registered name. |
| Project / solution name | Adept. |
| Name (leader) | Team to complete privately in the submission PDF. |
| Email and phone (leader) | Team to complete privately in the submission PDF. |
| University affiliation(s) | Team to confirm. |
| Live prototype URL | No public deployment verified. Local prototype: `http://localhost:3000`; API docs: `http://localhost:8000/docs`. These localhost addresses are not judge-accessible public URLs. |
| Code repository URL | [pecel-lelele/adept](https://github.com/pecel-lelele/adept); verify public visibility or grant judges access before submission. |

## 2. Architecture and technology stack

### 2.1 System architecture overview

<!-- answer:start technical-2.1 limit=200 -->
Adept uses a Next.js interface for learners and organisation reviewers. Server-side actions and
a typed API client call FastAPI; signed local-account sessions are held in an httpOnly cookie.
FastAPI validates requests with Pydantic and reads PostgreSQL for profiles, catalogue records,
trend snapshots, plans, progress and organisation membership.

The offline trend pipeline uses a pre-trained MiniLM sentence encoder to map research text to
skills, combines it with a committed labour baseline and validates a snapshot before publication.
Matching and pathway generation use deterministic rules. No generative model is called by the
application; only a null LLM provider is implemented.

Docker Compose runs web, API and PostgreSQL with pgvector under the project name adept. The
database has a persistent volume. GitHub Actions defines quality checks, a weekly source audit
and a trend-refresh job that requires a configured database secret. Public cloud hosting is
planned, not verified. Every recommendation carries dated sources, scenario and estimate metadata.
<!-- answer:end technical-2.1 -->

**Diagram appendix:** [current system block diagram](SUBMISSION_PROPOSAL.md#31-conceptual-tech-stack),
[full Mermaid collection](../README.md#3-system-architecture), and the
[offline pan-and-zoom viewer](diagrams/index.html). Diagram relationships are traced to routers,
Compose services and migrations. Schema excerpts distinguish enforced foreign keys from logical joins.

### 2.2 Languages, frameworks and libraries

Frontend versions below are declared in [`package.json`](../src/web/package.json). Backend
requirements are ranges in [`requirements.txt`](../requirements.txt), not exact lock versions.
Keep the resolved environment inventory with the final build if exact versions are requested.
This is a direct-dependency inventory; transitive packages retain their own upstream notices.

| Name and version / constraint | Licence | Purpose in project |
|---|---|---|
| Python 3.11 | Python Software Foundation License | API, pipelines and tooling. |
| Node.js 22 in Docker; pnpm 10.29.3 | MIT | Frontend runtime and package management. |
| Next.js 16.2.12; React and React DOM 19.2.9 | MIT | Server rendering, routing and UI. |
| TypeScript 5.9.3 | Apache-2.0 | Strict frontend typing. |
| Tailwind CSS / PostCSS plugin 4.1.18 | MIT | Styling. |
| next-intl 4.4.0 | MIT | English, Bahasa Melayu and Chinese. |
| lucide-react ^1.61.0 | ISC | Interface icons. |
| class-variance-authority 0.7.1 | Apache-2.0 | Component variants. |
| clsx 2.1.1; tailwind-merge 3.3.1 | MIT | CSS class composition. |
| @fontsource-variable/inter ^5.3.0 | MIT package; SIL OFL 1.1 font | Installed font dependency; current global UI styling uses Arial. |
| openapi-fetch 0.14.1; openapi-typescript 7.9.1 | MIT | Typed API client and generated contracts. |
| @types/node 22.20.5; @types/react 19.2.18; @types/react-dom 19.2.7 | MIT | Development type definitions. |
| FastAPI >=0.115,<1 | MIT | HTTP API and OpenAPI. |
| Pydantic >=2.7,<3; pydantic-settings >=2.3 | MIT | Contracts and configuration. |
| Uvicorn standard >=0.30 | BSD-3-Clause | ASGI service. |
| psycopg binary and psycopg-pool >=3.2 | LGPL-3.0; bundled binary components have additional notices | PostgreSQL access and pooling. |
| python-multipart >=0.0.9 | Apache-2.0 | Multipart CV uploads. |
| PyJWT >=2.8,<3 | MIT | Optional Supabase JWT verification. |
| PyMuPDF >=1.24,<2 | AGPL-3.0 or commercial | In-memory PDF text extraction; review distribution obligations before release. |
| PostgreSQL 16; pgvector | PostgreSQL License | Relational storage and 384-dimensional vectors; extension version is not pinned in Compose. |
| sentence-transformers 3.3.1; CPU torch 2.5.1 in trend workflow | Apache-2.0; BSD-3-Clause | Offline embeddings, installed in the trend job rather than the API image. |
| pytest >=8.2; httpx >=0.27; Ruff >=0.6 | MIT; BSD-3-Clause; MIT | Tests, HTTP test client and Python quality checks. |
| ESLint 9.39.5; eslint-config-next 16.2.12 | MIT | Frontend linting. |
| uv | MIT or Apache-2.0 | Python environment tooling; tool version is environment-dependent. |
| Mermaid 11.12.0 | MIT | Documentation-only vector diagram generation; generated viewer requires no runtime download. |

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
| Generative AI APIs | None in the running application | `LLM_PROVIDER=none`; no non-null provider implementation. |

The BLS baseline is committed data, not an external API called by the running recommendation
service. Model weights may be downloaded from Hugging Face when preparing the offline encoder;
that is a model acquisition step, not hosted inference. Do not include API keys in this document.

### 3.2 Cloud platforms and deployment

| Service and provider | Plan / region | Purpose and verified status |
|---|---|---|
| GitHub repository / Actions | Account plan and runner region not verified; workflows use `ubuntu-latest` | Version control; quality CI; source audit and conditional trend publication. Workflow presence does not prove a successful run. |
| Local Docker Compose | Local Windows Docker Desktop; no cloud region | Current verified prototype: web `:3000`, API `:8000`, PostgreSQL host `:5433`, persistent `adept_pgdata`. |
| Replit, or Vercel + Render | Planned; plan and region not selected | Candidate web/API hosts in project planning; no public deployment verified. |
| Supabase PostgreSQL / Auth | Optional/planned; plan and region not configured for this local stack | Managed database candidate. API has a JWT-verification path; Compose runs local account authentication. |
| Runpod | Optional proposal only; no plan or region verified | Possible future model hosting. No model service is deployed by this repository configuration. |
| Other cloud storage / hosted inference / analytics | None evidenced in the reviewed runtime configuration | Team must add any services used outside this checkout before submission. |

## 4. AI tools, models and datasets

### 4.1 AI models used in the solution

| Model and version | Source / provider | Licence / terms | Usage |
|---|---|---|---|
| [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Sentence Transformers model repository on Hugging Face | Apache-2.0 | Pre-trained sentence encoder; no team fine-tuning. Offline 384-dimensional sentence/skill embeddings and cosine matching, threshold 0.55. Model revision is not pinned by the current code. |
| Runtime generative model | None | Not applicable | `LLM_PROVIDER=none`; deterministic recommendations. A future provider must be implemented and disclosed before use. |

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

Counts below describe committed seed files as inspected on 22 October 2026, not the contents
of every deployed database. No model was fine-tuned on these fixtures.

| Dataset name | Source / URL | Type | Personal data? | Licence / terms and use |
|---|---|---|---|---|
| Custom skill and role catalogue: 113 skills, 7 roles | [Taxonomy seed](../src/data/seed/taxonomy/) | Team-curated / synthetic catalogue | No | Team curation; upstream source references retained where supplied. Not a complete official ESCO/O*NET import. Used for extraction and matching. |
| arXiv cs.AI research signal | [Ingest](../src/pipelines/trends/arxiv_ingest.py), [arXiv terms](https://info.arxiv.org/help/api/tou.html) | Public | No learner data; raw feed metadata may contain public author names | Provider terms and per-article licences apply; avoid a blanket CC0 claim. Research text is used offline for aggregated skill signals. |
| BLS 2023–2033-derived labour baseline | [Committed baseline](../src/data/seed/labor_decay.csv), [BLS source](https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm) | Public / team-derived | No | US government source with attribution; occupation-to-skill mapping is a team method. The linked live BLS table can advance to newer editions. |
| Canonical skill exposure and historical snapshots | [Seed data](../src/data/seed/), [methodology](skill-exposure-methodology.md) | Curated / public-derived | No | Reviewer-assigned exposure scores and dated replay fixtures; not measured probabilities. October 2026-labelled demo snapshots replay October 2024 research windows, disclosed in provenance. |
| 17 SDG goals and 169 targets | [UN API](https://unstats.un.org/SDGAPI/v1/sdg/Goal/List), [seed](../src/data/seed/sdg/) | Public | No | UN data terms and attribution; official target wording retained. |
| 13 role-target and 127 skill-target links | [Mapping seed](../src/data/seed/sdg/), cited evidence per record | Team-curated | No | Draft team interpretations with reasons and evidence; not official UN endorsements. Human review status is explicit. |
| 34 course records | [Catalogue sources](../src/api/app/features/pathway/catalogue_sources.py), [seed](../src/data/seed/courses/) | Public facts / curated | No | Microsoft, Coursera, local providers and universities retain their respective terms. Prices and HRD Corp notes are dated estimates, not entitlement guarantees. |
| Exchange rates | [BNM OpenAPI](https://api.bnm.gov.my/) | Public | No | BNM terms and attribution; used for estimated MYR costs. |
| Synthetic personas, organisation members and CVs | [Fixtures](../tests/api/profile/fixtures/cvs/), [persona seed](../src/data/seed/personas/), [organisation seed](../src/data/seed/org/) | Synthetic | No real identities | Team-created evaluation and test data only. Local sign-up demo must use invented details and synthetic CVs. |

### 4.3 AI-assisted development tools

**Yes.** This documentation session uses OpenAI Codex. Repository context files for other
assistants establish support for those tools, not proof that each was used.

| Tool and version | Extent of use | Used for |
|---|---|---|
| OpenAI Codex desktop; exact app/model identifier not recorded in the deliverable | Major for this documentation revision | Repository inspection, Markdown drafting, recovery of Mermaid sources, interactive viewer implementation and verification. Final content requires team review. |
| Other AI coding, chat, image or design tools used by teammates | Team to confirm before signing | Add actual product/model versions and extent; do not infer usage from `CLAUDE.md`, `GEMINI.md` or installed tools. |

**Review and responsibility (maximum 100 words):**

<!-- answer:start technical-4.3 limit=100 -->
This revision checks technical claims against dependency manifests, routers, scoring code,
migrations and seed files. Mermaid diagrams are rendered and viewer interactions checked.
The project quality gate is run and its actual outcome reported, including existing failures.
Public claims link to primary sources; unverified team, hosting, sponsor and legal declarations
remain explicitly pending. Team members must review the diff, confirm ownership and usage,
and approve the final submission. Automated checks do not establish legal compliance or
workforce outcomes.
<!-- answer:end technical-4.3 -->

## 5. Sponsor-provided resources

**Yes / No: team to confirm.** No sponsor API, cloud credit or sponsor-hosted service is
evidenced by the running local configuration. Workshop attendance, mentoring and credits
cannot be determined from source files.

| Sponsor | Resource | How used |
|---|---|---|
| None verified in this checkout | No confirmed sponsor-provided API, credits, platform or dataset | Local Docker and public sources support the current prototype. Team must add any actual sponsorship or mentoring before selecting Yes/No. |

**Essential or replaceable (maximum 100 words):**

<!-- answer:start technical-5 limit=100 -->
No sponsor resource is currently a demonstrated core dependency. The prototype runs locally
with public sources and an offline encoder. The proposed web/API host can be replaced by a
service that supports the existing containers, environment configuration and PostgreSQL
connectivity. Optional future model hosting is unnecessary for current deterministic
recommendations. Confirm actual sponsor usage with every member before signing.
<!-- answer:end technical-5 -->

## 6. Security, privacy and responsible use

### 6.1 Data handling and privacy

<!-- answer:start technical-6.1 limit=150 -->
The hackathon demonstration uses synthetic identities, organisations and CVs only. The
application can store account names and emails, scrypt password hashes, skills, learning
preferences, memberships, plans, progress and evidence links in PostgreSQL. CV uploads are
parsed in memory; the original file is not stored. Extracted skills are saved only after
confirmation. No learner profile is sent to a generative AI service.

Signed sessions use httpOnly cookies; authorisation restricts organisation access. Local ports
bind to loopback. Upload limits, rate limits and text filtering are implemented. Certificate
link checks contact provider pages, exposing ordinary request metadata, not a full profile.

Persistent records remain until deliberately removed; no automatic retention/deletion policy
is implemented. Docker volume retention is not a privacy policy. HTTPS, managed secrets,
backup access and a documented retention process require deployment review before any
broader use. Do not use real personal data in the competition demo.
<!-- answer:end technical-6.1 -->

### 6.2 Known limitations and risks

<!-- answer:start technical-6.2 limit=150 -->
Research attention is a proxy for skill demand; US labour projections do not establish
Malaysian vacancies. The small curated catalogue limits coverage. Seed snapshots contain
historical replay data, so publication date and observed period must both be shown.
Scenario and exposure scores are heuristic estimates, not probabilities or calibrated confidence
intervals. SDG links are interpretations pending review, not verified social outcomes.

PDF skill extraction can miss aliases and scanned documents; users confirm skills. Provider
page reachability does not prove certificate ownership. Prices, funding eligibility and API
availability can change. Mitigations include dated sources, validation before snapshot
publication, catalogue-ID checks, counterfactual tests, manual evidence review and explicit
estimate labels. The null LLM provider avoids runtime generative hallucination; future providers
must pass the ID validator. Local deployment success does not establish public hosting,
security certification, fairness across all populations or improved employment outcomes.
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
[null provider](../src/api/app/core/llm/provider.py) ·
[trend workflow](../.github/workflows/trends-refresh.yml) ·
[source audit](../.github/workflows/data-sources.yml) ·
[catalogue sources](../src/api/app/features/pathway/catalogue_sources.py).
