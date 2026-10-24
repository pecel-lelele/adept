# F8 Guardrails & transparency (M3)

- **Feature ID**: F8
- **Owner**: M3
- **API code**: `src/api/app/core/llm/` (provider interface, gateway, ID validator)
- **Web code**: `src/web/src/features/guardrails/` (About page)
- **Translations**: `src/web/messages/{en,ms,zh}/guardrails.json`

## Status

`LLM_PROVIDER=none` is the safe default. The presentation setup uses Runpod `glm-5.3` as the
primary model at the supplied public OpenAI-compatible endpoint, with separately authenticated
Google Gemini models only on primary failure. Runpod uses `RUNPOD_API_KEY`, Gemini uses
`GEMINI_API_KEY`; both stay in root `.env` or deployment secrets and only the API container
receives them. Requests use low reasoning and capped output, share one request deadline and
reserve time for the fallback. `/about`, API replies and logs disclose the actual provider/model.
The gateway redacts PII and filters prompt injection
before any prompt, rejects unknown IDs, has a circuit breaker, logs every call, and
`select_ids_or_fallback` degrades to deterministic logic. Related F8 code:
`app/core/security/` (rate limit, body limit, headers, sanitiser, PII, Supabase JWT),
`app/core/fairness.py`, and `app/features/guardrails/` (`/guardrails/disclosure`, `/sources`,
`/fairness`, rendered on `/about`).

## Goal and tasks (from docs/tasks.md)

**Goal:** meet the handbook's AI disclosure and "never invent" rules across the whole app.

**Open choices:** LLM provider and model (must be disclosed), prompting approach, validation approach.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | LLM gateway: model only selects database IDs; validator rejects unknown IDs; structured output; logging | All features using an LLM |
| Preliminary | Courses and SDG links carry source, URL and date | F5, F6 |
| Preliminary | About page + README section: model used, purpose, methodology, limitations | Core |
| Optional | Chatbot coach grounded in profile and catalogue, through the same validator; only if everything else is done | |

## Pipeline

| Stage | Choice | Notes |
|---|---|---|
| Source | catalogue (id → label) supplied by the calling feature | the model can only answer with those IDs |
| Preprocessing / cleaning | `clean_extracted_text` (injection patterns → `[filtered]`) then `redact_text` (email, NRIC, passport, phone) | patterns from KerjaCerdas, Malaysian formats |
| Features | none | |
| Model / method | none configured; provider protocol + structured output | name the model here, on `/about` and in the README when enabled |
| Evaluation | tests: unknown IDs rejected, prompts redacted, breaker opens/closes, fallback used; CI sweep: every recommendation endpoint returns dated sources; fairness scan of every API input and DB column | `tests/api/llm`, `tests/api/guardrails` |
| Serving | `select_ids`, `select_ids_or_fallback`; `/guardrails/*` endpoints | |
