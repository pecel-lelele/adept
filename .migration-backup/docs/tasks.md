# Tasks by Feature

This document defines feature scope and ownership. For current behaviour, use the
[project README](../README.md), each feature's `FEATURE.md`, and the
[decisions log](decisions.md). Test results belong to the relevant PR.

Work is organised **per feature**. Each feature has an owner who leads it end to end (data → logic → API → page) and decides its additional tech. The same breakdown is in `aiversecity_team_tasks.xlsx` for progress tracking.

- **Primary stack (fixed for all features):** Python, Next.js (TypeScript), PostgreSQL, Git + GitHub.
- **Open choices:** listed per feature below. The owner decides and records each choice in `docs/decisions.md`.
- **Phases:** Preliminary (proposal + live demo of trend signals feeding role matching) → Final (all six must-haves) → Optional.

## Overview

| Feature | Owner | Handbook items covered |
|---|---|---|
| F1 Skills profile intake | M2 | Must-have 1; guardrail: synthetic data |
| F2 AI-trend signal layer | M1 | Must-have 2; guardrail: sources; good-to-have: trend replay / re-planning |
| F3 Scenarios & uncertainty | M1 | Must-have 6 |
| F4 Future-role matching | M2 | Must-have 3; good-to-haves: SDG slider, fairness checks |
| F5 Reskilling pathway | M3 | Must-have 4; good-to-have: progress + badges |
| F6 SDG mapping | M3 | Must-have 5 |
| F7 Organisation mode | M4 | Good-to-haves: HR view, aggregated SDG view |
| F8 Guardrails & transparency | M3 | Guardrails: catalogue-only, sources, LLM disclosure; optional chatbot |
| Core | M4 | App shell, human-in-charge messaging, multi-language + mobile, integration, deploy, submission |

---

## F1 Skills profile intake (M2)

**Goal:** capture current skills **and potential** via CV upload, form or questionnaire.

**Open choices:** PDF parser, extraction method (LLM / NER / rules / hybrid), embedding or similarity method, form library.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Questionnaire: segment (working / graduate / switcher), interests, hours per week, learning style, budget, HRD Corp eligibility | Core (UI kit) |
| Preliminary | CV pipeline: parse → clean text → extract skills → normalise to taxonomy → confidence score | F4 (taxonomy) |
| Preliminary | Skill confirmation screen: user edits extracted skills and levels | |
| Preliminary | 3–5 synthetic personas and fake CVs (Aisyah, Wei Jie, Ravi) + a synthetic team for the HR demo | F7 |
| Final | Capture potential: interests, transferable skills for switchers, current-role risk for working adults | F2, F3 |

## F2 AI-trend signal layer (M1)

**Goal:** at least one updatable AI/job-market source; source and date visible; no hard-coded lists.

**Open choices:** data sources, HTTP/data libraries, scheduler, trend scoring formula, snapshot storage format.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Choose ≥1 updatable public source (2 if possible); check licence and stability | |
| Preliminary | Ingestion: fetch → clean → map to taxonomy IDs → store as dated, versioned snapshot | F4 (taxonomy) |
| Preliminary | Cached fallback snapshot for when the source is down | |
| Preliminary | Trend scores per role/skill: growth, AI exposure, automation vs augmentation | |
| Preliminary | Future Skills Radar page: rising / stable / declining with "data as of [date], source: [name]" | Core (UI kit) |
| Preliminary | Every trend response includes source, URL and date | |
| Final | Scheduled automatic refresh | |
| Final | Admin pages: sources, snapshot versions, manual refresh | |
| Final | Snapshot diff: what changed and why | |
| Final | Trend replay: switch snapshot date, rankings change | F4, Core |
| Final | Re-planning: new snapshot → recompute matches and pathways → notify users | F4, F5 |

## F3 Scenarios & uncertainty (M1)

**Goal:** more than one future scenario; predictions clearly marked as estimates.

**Open choices:** scenario parameters and their sources, forecasting method, range method.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Define moderate vs fast AI disruption parameters | |
| Preliminary | Outlook per role per scenario with low/high ranges | F2 |
| Preliminary | Scenario/outlook endpoint used by matching | F4 |
| Preliminary | "Estimate" labelling on every prediction | Core (UI kit) |

## F4 Future-role matching (M2)

**Goal:** ranked future roles with an explainable score and a clear skills gap.

**Open choices:** taxonomy (ESCO / O*NET / hybrid), scoring formula and weights, retrieval method, evaluation metrics, fairness test design, chart library.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Load skill and role taxonomy as shared reference data | F1, F2, F6 |
| Preliminary | Explainable score: skill overlap + trend outlook (per scenario) + interest fit, shown as parts | F3 |
| Preliminary | Skills gap: have / partial / missing | |
| Preliminary | Matches page and role detail: score breakdown, gap, sources, SDG badges; re-rank on scenario toggle | F6, Core |
| Preliminary | Evaluation on labelled synthetic personas (e.g. precision@k, nDCG@k) | |
| Final | SDG-weighted ranking slider | F6 |
| Final | Fairness: age, gender, background excluded from matching | |
| Final | Counterfactual fairness tests (swapped personas → identical results) | |
| Final | Team-level aggregates for the HR heatmap | F7 |

## F5 Reskilling pathway (M3)

**Goal:** ordered learning plan with estimated time, using free/low-cost and HRD Corp-claimable resources.

**Open choices:** course sources, prerequisite graph method, time-estimation approach.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Course catalogue: real URLs, hours, cost, HRD Corp-claimable flag (manually verified, with date) | |
| Preliminary | Pathway page (static preview for the demo persona) | Core |
| Final | Prerequisite graph and step ordering | F4 |
| Final | Time estimate: total weeks from course hours and the user's hours per week | F1 |
| Final | Progress tracking + skill badges; match score rises as steps complete | F4 |
| Final | Recompute pathway on new trend data | F2 |

## F6 SDG mapping (M3)

**Goal:** every role and skill tagged to at least one SDG; show how the chosen path contributes. Meaningful, not decorative.

**Open choices:** SDG data source, mapping method (embedding, LLM-assisted, manual), review process.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Load official 17 SDGs and their targets | |
| Preliminary | Map roles and skills to target level (e.g. 7.2, 4.4) with a one-line reason; human review for demo roles | F4 |
| Preliminary | SDG badge data for roles and skills | F4 |
| Final | Personal SDG contribution panel | |

## F7 Organisation mode (M4)

**Goal:** serve HR/L&D managers and career centres with team-level views.

**Open choices:** chart library, invite mechanism, export format.

| Phase | Task | Works with |
|---|---|---|
| Final | Organisation setup (company / institution) and member invites | Core |
| Final | Team skills-gap heatmap | F4 |
| Final | Team reskilling plan: assign to members, members can adjust | F5 |
| Final | Aggregated SDG view for a company or cohort | F6 |
| Final | Institution extras: advisor notes, report export | |

## F8 Guardrails & transparency (M3)

**Goal:** meet the handbook's AI disclosure and "never invent" rules across the whole app.

**Open choices:** LLM provider and model (must be disclosed), prompting approach, validation approach.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | LLM gateway: model only selects database IDs; validator rejects unknown IDs; structured output; logging | All features using an LLM |
| Preliminary | Courses and SDG links carry source, URL and date | F5, F6 |
| Preliminary | About page + README section: model used, purpose, methodology, limitations | Core |
| Optional | Chatbot coach grounded in profile and catalogue, through the same validator; only if everything else is done | |

## Core (M4)

**Goal:** one coherent, deployed app that judges can try in minutes.

**Open choices:** UI component library and styling, auth provider, i18n library, hosting.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Landing page with Individual / Organisation switch, data-freshness badge, demo buttons | |
| Preliminary | App shells + journey stepper (steps 1–4) | |
| Preliminary | Shared UI: scenario toggle, source badge, estimate label, SDG badge, score breakdown | All |
| Preliminary | Demo persona login (no signup) | F1 |
| Preliminary | Human-in-charge messaging; user explicitly chooses a target role; consent screen | F4, F5 |
| Preliminary | End-to-end integration: intake → radar → matches → pathway | All |
| Preliminary | Shared contracts and output format (sources, snapshot date, scenario, estimate) | All |
| Preliminary | Deploy + public repo + README | |
| Preliminary | Assemble proposal, demo script | All |
| Final | Multi-language EN / BM / 中文 | All |
| Final | Mobile-friendly, low-bandwidth layout | |
| Final | Pitch deck and demo video | All |

## Shared by everyone

- Write your feature's proposal section plus one "hardest risk + fallback": F2 trend data reliability, F4 matching quality, F8 AI inventing jobs/courses.
- Add a `docs/decisions.md` entry for every change.

---

## Critical path for the preliminary demo

```
F4 taxonomy ─┬─> F2 ingestion ─> F2 scoring ─> F3 scenarios ─┐
             └─> F1 intake ───────────────────> F4 matching ─┴─> Core integration ─> deploy + demo
F6 SDG mapping ───────────────────────────────> SDG badges on matches
```

Everyone builds against mock data first, so nobody has to wait to start.
