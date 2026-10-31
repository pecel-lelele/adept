# Project Context: Aiversecity Future-Ready Workforce

This is the single source of truth for what we are building and why.
Both `CLAUDE.md` and `GEMINI.md` import this file. Edit it only through a PR approved by the whole team.

---

## 1. Competition

| Item | Value |
|---|---|
| Event | SDC XMUM Hackathon, Domain 1 |
| Domain | The Aiversecity Future-Ready Workforce Domain |
| Domain sponsor | Aiversecity |
| Platform sponsors | Replit, Runpod |
| Difficulty | Intermediate |
| Main SDG | SDG 4 Quality Education |
| Relevant SDGs | SDG 5 Gender Equality, SDG 8 Decent Work and Economic Growth, SDG 9 Industry, Innovation and Infrastructure, SDG 10 Reduced Inequalities |
| SDG targets | 4.4 relevant skills for decent jobs, 4.3 lifelong technical and vocational learning, 8.2 productivity through innovation, 8.5 full and productive employment |
| Country context | Malaysia |

## 2. Problem statement (verbatim)

> How might we build an AI-powered solution that continuously tracks AI advancement to predict which skills and jobs will emerge or decline, matches today's workforce and tomorrow's talent to the right future roles, and generates personalised reskilling pathways, while showing how each role and skill connects to the 17 UN Sustainable Development Goals?

## 3. Background

- AI is changing which jobs exist faster than training programmes and skills frameworks can be updated.
- In Malaysia, 56% of professionals use AI tools at work, but only 26% have had formal training (Hays Asia Salary Guide 2025).
- MOSTI has said more than 600,000 workers will need reskilling within three to five years.
- Aiversecity's position: AI should be a partner to people, not a replacement.
- Current gaps: workers don't know which AI skills to learn; employers can't tell which roles to train for; learning pathways are static lists that go out of date quickly.
- Because AI progress is unpredictable, a one-time skills assessment is not enough. The system must keep learning as the technology moves.
- Future-ready skills are also sustainability skills (clean energy, health, smart agriculture, responsible AI).

## 4. Who we are building for

1. Working adults at risk of job displacement
2. Fresh graduates and career switchers deciding where to go next
3. HR and learning-and-development (L&D) managers planning how to reskill their teams
4. TVET and university career centres advising students

## 5. What to build (handbook journey)

A working web app or dashboard (proof of concept is acceptable) that takes a user from "who I am today" to "where I can be in the AI era":

1. **Tell us about yourself**: skills, experience and interests via CV upload, form or short questionnaire.
2. **See the Future Skills Radar**: which skills and roles are rising or declining, based on identifiable AI-trend and job-market signals.
3. **Get matched**: best-fit future roles, each with a match score and a skills-gap breakdown.
4. **Follow a pathway**: a step-by-step reskilling plan, with every recommended role and skill linked to one or more of the 17 SDGs.

## 6. Must-have features (all required in the final product)

| # | Feature | Acceptance criteria from the handbook |
|---|---|---|
| 1 | Skills profile intake | Capture current skills **and potential** via CV upload, form or questionnaire. |
| 2 | AI-trend signal layer | At least one **updatable** source of AI and job-market trends (job postings, news/research feeds, open datasets). **Show the source and its date.** Hard-coded lists alone do not count. |
| 3 | Future-role matching | Rank suitable future roles with an **explainable** match score and a clear skills gap. |
| 4 | Personalised reskilling pathway | **Ordered** learning plan with **estimated time**, using free or low-cost resources (online courses, HRD Corp-claimable programmes, etc.). |
| 5 | SDG mapping | Tag **each role and skill** to at least one SDG, and show how the user's chosen path contributes to the goals. |
| 6 | Handling uncertainty | Show **more than one future scenario** (e.g. moderate vs fast AI disruption) and make clear that predictions are **estimates**. |

Preliminary round: the proposal explains how each one will be delivered; the demo shows the most important one working.

## 7. Good-to-have features (optional, boost Innovation or Problem-Solution Fit)

- Employer / HR view: workforce-level skills-gap heatmap and reskilling plan for a team or company
- Automatic re-planning when new AI-trend data changes recommendations
- Inclusive design: English, Bahasa Malaysia, Chinese; low-bandwidth, mobile-friendly
- Learner motivation: progress tracking, skill badges
- Fairness checks: recommendations must not discriminate by age, gender or background
- SDG contribution view aggregated for a person, a company or a region

## 8. Rules and boundaries (HARD CONSTRAINTS, never violate)

- **Data**: public, open or synthetic data only. No real personal data or real CVs. Demo uses sample profiles.
- **AI disclosure**: if a language model is used, name it.
- **Guardrails**: every recommendation must cite a source. The system must **not invent** jobs, courses or statistics.
- **Human-centred**: AI supports human career decisions; it does not replace human judgement or make hiring decisions.
- **Technology**: free choice of stack.
- **Out of scope**: full course content, payment systems, real recruitment integrations.

## 9. What success looks like (sponsor's words, paraphrased)

A new user gets from profile to ranked future roles and an actionable pathway **in minutes**. Every recommendation is transparent about its source, the **output visibly changes when the trend data changes**, and the SDG link is **meaningful, not decorative**.

## 10. Judging context

For final-round preparation, use the [current evidence checklist](submission/rubric-check.md).
The supplied Domain 1 Finalist Guide provides six criteria (25/25/20/15/10/5), mapped in
the current evidence checklist. The
table below is **historical preliminary guidance only**.

### Historical preliminary round rubric

| Criterion | Weight | What judges look for |
|---|---|---|
| Innovation & Creativity | 30% | A sharply framed slice (specific user + moment of need). Goes beyond "upload a CV and ask a chatbot for jobs". Originality in how trend signals become skill forecasts, how scenarios are modelled, or how SDG links change user choices. |
| Problem-Solution Fit | 25% | Covers the whole chain: tracking AI advancement, predicting emerging/declining skills and jobs, matching, personalised pathways, SDG connection. Explains delivery of all six must-haves. Keeps humans in charge. |
| Feasibility of Build | 25% | Rough working version of the most important feature, shown live and backed by the GitHub repo. Usually **the trend signal layer feeding role matching**. Names the hardest risk and a fallback, using only public or synthetic data. |
| Clarity of Proposal | 20% | Problem → approach → expected outcome. A cold listener could explain it back, including who the user is and what they walk away with. Follows submission format and length limits. |

Judging notes: score = weight × band percentage. GitHub repo link is required, must be public or accessible, and must reflect the demo. Preliminary score does not carry forward; the final round has a different rubric.

---

## 11. Our product decisions (team-agreed)

### 11.1 Two modes, not four apps

The landing page has a **switch: Individual | Organisation**.

| Mode | Covers | Variation handled by config |
|---|---|---|
| Individual (`/app`) | Working adults, fresh graduates, career switchers | `learner.segment = working \| graduate \| switcher` changes intake questions and one screen (current-role risk vs transferable skills) |
| Organisation (`/org`) | HR/L&D managers, TVET/university career centres | `organization.type = company \| institution` changes labels (team vs cohort) and 1–2 features (HRD Corp team plan vs advisor notes) |

Admin (`/admin`) is internal only, not shown on the landing page.

### 11.2 Journey mapping

| Handbook step | Individual mode | Organisation mode |
|---|---|---|
| 1. Tell us about yourself | Personal CV / form / questionnaire | Invite members (each completes intake) + organisation profile |
| 2. Future Skills Radar | Radar highlighted for the user | Radar highlighted for the industry/programme |
| 3. Get matched | Ranked roles + plain-language "what would raise this score" tips + gap | Team skills-gap heatmap + target roles |
| 4. Follow a pathway | Personal plan + SDG contribution | Group plan, assigned to members (members can adjust) + aggregated SDG |

Scenario toggle and source links appear in steps 2–4; estimate cues sit in each Sources link (M4-100).

### 11.3 Routes

```
/                   home: Individual | Teams switch; CV upload with an instant partial
                    result (skills found, their trend, best-fit role); the rest unlocks
                    with a free account
/auth/signup        create an account (individual, or organisation + join code)
/auth/login         sign in
/auth/join?code=    join an organisation (sign-up with the code, or in-app)
/app                learner home: next step, top roles, own skills on the radar, plan, SDGs
/app/onboarding     step 1: four-step intake (stage, interests, time/budget, skills)
/app/profile        step 1 result: my skills, organisation
/app/radar          step 2
/app/matches        step 3 (+ /app/matches/[roleId])
/app/pathway        step 4 (+ /app/progress, /app/courses, /app/sdg)
/org                organisation home: invite → waiting → act
/org/members        join code, intake status, remove members
/org/radar          step 2 (organisation context)
/org/gaps           step 3 (heatmap)
/org/plan           step 4 (group plan for a target role)
/org/sdg            aggregated SDG contribution (+ /org/courses, /org/verify)
/org/setup          organisation settings and join code
/org/programmes     manager programme list and creation wizard
/org/funding        annual budgets, purchase approvals and payment records
/work               employee workspace: employer programmes and sharing
/work/plan          review a learning agreement
/work/skills        control skill and personal-completion sharing
/work/progress      organisation-scoped progress and evidence
/work/funding       employee funding requests and claims
/about              LLM disclosure, methodology, data sources, limitations
/admin/*            data sources, snapshots (internal)
```

### 11.4 Features and owners

| ID | Feature | Owner |
|---|---|---|
| F1 | Skills profile intake (CV parsing, skill extraction, normalisation, questionnaire, confirm) | M2 |
| F2 | AI-trend signal layer + Future Skills Radar + admin data pages + re-planning trigger | M1 |
| F3 | Scenarios and uncertainty (scenario parameters, outlook model, ranges) | M1 |
| F4 | Future-role matching (explainable score, gap, fairness, evaluation) | M2 |
| F5 | Reskilling pathway (course catalogue, ordering, time estimate, progress) | M3 |
| F6 | SDG mapping (role/skill → SDG target + reason, contribution views) | M3 |
| F7 | Organisation mode (members, heatmap, group plan, advisor notes) | M4 |
| F8 | Guardrails and transparency (LLM gateway, ID validation, sources, About page) | M3 |
| Core | Landing, auth, shells, dashboard, design system, i18n, deploy, proposal | M4 |

### 11.5 Personas (design and test fixtures only)

The live app has no built-in personas: the demo runs through real sign-up, intake and
matching, and everything is stored in PostgreSQL. The personas below guide design and
are installed only by the automated tests (`tests/harness/fixtures.py`) and the
matching evaluation benchmark (`src/data/seed/personas/`).


- **Aisyah**, 34, bank operations executive in Kuala Lumpur. Employer announced AI automation of back-office work. 6 hours/week to learn, HRD Corp eligible. Primary demo persona.
- **Wei Jie**, 22, fresh diploma graduate in IT, unsure where to start.
- **Ravi**, 41, logistics supervisor switching careers.
- **Demo company**: mid-size Malaysian bank operations team of 25 synthetic employees.
- **Demo institution**: polytechnic career centre with one synthetic cohort.

### 11.6 Locked core tech stack

| Layer | Choice |
|---|---|
| Monorepo tooling | `Makefile` at root, `pnpm` for JS, `uv` for Python |
| Frontend | Next.js (App Router, TypeScript) + Tailwind CSS + shadcn/ui; `next-intl` for EN/BM/ZH |
| Backend | FastAPI + Pydantic v2 (Python 3.11) |
| Database | Replit integrated PostgreSQL for deployment; PostgreSQL 16 + `pgvector` via Docker for local development and CI |
| Migrations | `src/db/migrate.py` with timestamped, dbmate-compatible SQL files |
| Auth | `AUTH_MODE=demo` uses signed local accounts stored in PostgreSQL, including on Replit; test-only raw-user switches are never production settings |
| Contracts | Pydantic models → OpenAPI → generated TypeScript types |
| Testing | `pytest`, `ruff`, ESLint, TypeScript `tsc --noEmit` |
| Quality gate | `make check` run locally before every PR |
| Deploy | Replit (sponsor): public Next.js and private FastAPI; optional model inference on RunPod (sponsor) |

### 11.7 Open decisions (owned per feature, recorded in `docs/decisions.md`)

These are NOT locked. Each owner decides and records the choice as an entry in their own section of `docs/decisions.md` (every change, not just these, gets an entry):

- F1: CV parser, extraction method (LLM vs NER vs rules), skill taxonomy (ESCO / O*NET), embedding model
- F2: trend data sources, refresh schedule, trend scoring formula
- F3: scenario parameters, outlook formula, uncertainty range method
- F4: matching formula and weights, retrieval method, evaluation metrics, fairness test design
- F5: course sources, prerequisite graph construction, time estimation
- F6: SDG mapping method, review process
- F8: LLM provider and model name (must be disclosed on `/about`)

### 11.8 Output contract rule (applies to every recommendation)

Every API response that contains a recommendation, score or trend includes:

```json
{
  "sources": [{"name": "...", "url": "...", "retrieved_at": "YYYY-MM-DD"}],
  "snapshot_date": "YYYY-MM-DD",
  "scenario": "moderate | fast",
  "is_estimate": true
}
```

## 12. Glossary

- **Snapshot**: one dated, versioned fetch of trend data from a source.
- **Outlook**: projected demand for a role or skill under a scenario.
- **Skills gap**: skills required by a role that the user lacks or has at a lower level.
- **HRD Corp**: Malaysia's Human Resource Development Corporation; employers can claim levy for approved training.
- **TVET**: Technical and Vocational Education and Training.
- **ESCO / O*NET**: public skill and occupation taxonomies.
