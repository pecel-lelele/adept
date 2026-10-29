# F1 Skills profile intake (M2)

- **Feature ID**: F1
- **Owner**: M2
- **API code**: `src/api/app/features/profile/` (router → service → repository → mocks)
- **Contracts**: `src/api/app/contracts/profile.py`
- **Web code**: `src/web/src/features/profile/`
- **Translations**: `src/web/messages/{en,ms,zh}/profile.json`
- **Seed data**: `src/data/seed/personas/`, `src/data/seed/taxonomy/`

## Status

Embedding suggestions require an existing catalogue index. Pre-build it with
`PYTHONPATH=src/api python -m app.features.profile.skill_match` using the configured
database. CV requests never build the index or wait for an in-progress build; an absent
or stale index falls back to exact catalogue matches without optional suggestions.

Implemented: in-memory PDF/DOCX/text parsing, catalogue aliases and user-confirmed skill
levels, questionnaire intake and PostgreSQL profiles. The web provides a four-step intake.
Unmatched wording and truncation are reviewable; uploads never mutate saved skills before
confirmation. See `cv_parser.py`, `service.py` and `tests/api/profile/`.

## Goal and tasks (from docs/tasks.md)

**Goal:** capture current skills **and potential** via CV upload, form or questionnaire.

**Open choices:** PDF parser, extraction method (LLM / NER / rules / hybrid), embedding or similarity method, form library.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Questionnaire: segment (working / graduate / switcher), interests, hours per week, learning style, budget, HRD Corp eligibility | Core (UI kit) |
| Preliminary | CV pipeline: parse → clean text → extract skills → normalise to taxonomy → confidence score | F4 (taxonomy) |
| Preliminary | Skill confirmation screen: user edits extracted skills and levels | |
| Preliminary | 3–5 synthetic personas and fake CVs (Aisyah, Wei Jie, Ravi) + a synthetic team for the HR demo | F7 |
| Final | Capture potential: interests, transferable skills for switchers, current-role risk for working adults | F2, F3 |

## Pipeline

Current deterministic intake pipeline:

| Stage | Choice | Notes |
|---|---|---|
| Source | In-memory sample CV or confirmed form | No raw upload storage |
| Preprocessing / cleaning | PDF/DOCX/text extraction, caps, NFKC and contact scrubbing | `cv_parser.py` |
| Features | Approved labels/aliases; skills-list entries read section by section | No invented IDs |
| Model / method | Alias matching, estimated levels, human confirmation; Gemini embeddings + pgvector cosine suggestions for unmatched entries | Suggestions are proposals the person adds |
| Evaluation | Format, safety, omission and persistence regressions | `tests/api/profile/` |
| Serving | CV, questionnaire and skill-confirmation endpoints | OpenAPI contracts |

## Catalogue omissions (2026-10-23 integration)

CV responses include `unmatched_terms`: up to 30 short entries from explicit
EN/MS/ZH skills lists which do not exactly match an approved label or alias.
These are unverified wording for transient review, not skill IDs. They are never
saved as profile skills, ranked, sent to an LLM or added to the taxonomy. Users
may search the existing catalogue and explicitly choose a valid equivalent.

This bounded rule cannot find every unfamiliar skill in prose or every CV layout.
Both guest preview and intake state that limitation, preserve truncation warnings,
and distinguish zero recognised catalogue skills from zero actual skills. Unknown
only previews produce no role or score. Existing exact aliases, level review,
file limits, scanned/encrypted PDF errors and ID validation remain in force.

## Section-aware review list and embedding suggestions (2026-10-23)

A skills list now ends at the next heading of any kind (any experience/education/project/
summary heading in EN/MS/ZH, or a short all-capitals line), so employers, job titles, dates
and sentences from other sections no longer appear in "Wording to review". Wrapped lines are
rejoined before splitting ("exception / handling."), words hyphenated at a line break are
rejoined, bullets and one-per-line lists still split per line, and "X (ABBR)" entries whose
halves both match are treated as matched (`skills_section_entries`, `unmatched_skill_terms`).

`skill_match.py` embeds the catalogue once (`gemini-embedding-001`, 768 dimensions, table
`catalogue_embeddings`, HNSW cosine index; re-embedded only when a label/alias changes) and,
for each unmatched entry, proposes the nearest skill when similarity >= 0.80 and it leads the
runner-up by >= 0.015; nothing is proposed when the nearest skill is already on the CV. Only
the short skills-list entries leave the API (PII-redacted), never the CV. With
`EMBEDDINGS_PROVIDER=none`, no key, or a provider failure, suggestions are empty and exact
matching is unchanged. This supersedes the "never sent to an LLM" note above for these short
entries only (decision M4-061).

## Alias-aware manual search and explicit resolver (2026-10-29)

`GET /api/v1/profile/skills/catalogue` now includes each skill's approved `aliases`.
The existing manual picker filters labels, IDs **and aliases** locally; for example,
"Microsoft Excel" finds Spreadsheet analysis without invoking the resolver or a model.

`POST /api/v1/profile/skills/resolve` is authenticated and accepts one query of at most
80 characters. Each tier contributes **at most one** catalogue candidate, deduplicated
by canonical skill ID (at most three overall). Exact labels/aliases need no model call.
Fuzzy matching uses NFKC/case/whitespace normalization and Python `SequenceMatcher`
(`autojunk=False`), taking each distinct skill's best label/alias score. Its gate is
`top_score >= 0.83` **and** `top_score - runner_up_score >= 0.05`. An above-threshold
fuzzy score with a smaller lead abstains before reaching the semantic tier.

Semantic matching still delegates to `skill_match.suggest`: **top-1 only**, cosine
`>= 0.80` and `top_score - runner_up_score >= 0.015`, using a ready index only.
Neither those constants nor the existing CV suggestion path change. Provider absence,
missing/stale index or failure retains deterministic candidates. Labels and IDs come
from the catalogue; each response includes the existing taxonomy attribution and date.
Suggestions never save skills; the person clicks Add and confirms their levels.

Typing only filters the local catalogue. "Find suggestions" explicitly submits a query
with at least **four letters/digits**. The server checks this minimum before semantic
matching too. A bounded, memory-only cache lives for one wizard session and keys normalized
queries, sharing pending requests and caching successful empty results; it is discarded
when the wizard unmounts. Errors can be retried. Changed queries hide stale responses.
The endpoint has a 10/minute rate bucket. No raw query is persisted or logged.

Small regression table at fuzzy threshold **0.83**, lead **0.05** (not a broad accuracy
benchmark; scores below are rounded, while the gate uses unrounded values):

| Input | Top score | Runner-up | Lead | Expected/result |
|---|---:|---:|---:|---|
| Pyhton | 0.833333 | 0.470588 | 0.362745 | Python programming — pass |
| Postgre SQL | 0.952381 | 0.476190 | 0.476190 | SQL — pass |
| Exel | 0.888889 | 0.571429 | 0.317460 | Spreadsheet analysis — pass |
| Kubernetes | 0.545455 | 0.500000 | 0.045455 | Abstain — pass |
| Blender | 0.555556 | 0.526316 | 0.029240 | Abstain — pass |
| r / c / go | — | — | — | Abstain (minimum length) — pass |
| project change management | 0.837209 | 0.809524 | 0.027685 | Abstain (lead < 0.05) — pass |

Production-function regressions: `tests/api/profile/test_skill_resolver.py`.
Client filtering/caching checks: `node --experimental-strip-types --test tests/profile-skill-search.test.ts`.
