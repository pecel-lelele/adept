# F8 Guardrails & transparency (M3)

- **Feature ID**: F8
- **Owner**: M3
- **API code**: `src/api/app/core/llm/` (provider interface, gateway, ID validator)
- **Web code**: `src/web/src/features/guardrails/` (About page)
- **Translations**: `src/web/messages/{en,ms,zh}/guardrails.json`

## Status

Skeleton: `LLM_PROVIDER=none`, so `NullProvider` raises `LLMUnavailableError` and callers
fall back to non-LLM logic. `validate_ids` rejects any ID not in the allowed set.
When a model is enabled, name it on `/about` and in the README.

## Goal and tasks (from docs/TASKS.md)

**Goal:** meet the handbook's AI disclosure and "never invent" rules across the whole app.

**Open choices:** LLM provider and model (must be disclosed), prompting approach, validation approach.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | LLM gateway: model only selects database IDs; validator rejects unknown IDs; structured output; logging | All features using an LLM |
| Preliminary | Courses and SDG links carry source, URL and date | F5, F6 |
| Preliminary | About page + README section: model used, purpose, methodology, limitations | Core |
| Optional | Chatbot coach grounded in profile and catalogue, through the same validator; only if everything else is done | |

## Pipeline

Fill this in as the feature takes shape (copy it into the `docs/decisions.md` entry).

| Stage | Choice | Notes |
|---|---|---|
| Source | | |
| Preprocessing / cleaning | | |
| Features | | |
| Model / method | | |
| Evaluation | | metric + result |
| Serving | | endpoint(s) |
