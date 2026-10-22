# Adi, the Adept assistant (Core, M4; guardrails F8)

- **API**: `POST /api/v1/assistant/chat` (signed-in learner or manager, or a visitor).
- **Contracts**: `src/api/app/contracts/assistant.py`
- **Web**: `src/web/src/components/adi/` (mascot, 3D mascot, chat panel), route handler
  `src/web/src/app/api/assistant/route.ts`.

## How an answer is made

1. `context.py` gathers the person's own data (profile, matches, saved plan, progress, team
   gaps, trend snapshot) or the public platform figures for visitors. Missing pieces are skipped.
2. `service.py` sends that CONTEXT plus the recent conversation to the configured model
   (`LLM_PROVIDER`, see `core/llm/provider.py`). The question is injection-filtered and
   PII-redacted first.
3. The model may name roles, skills, courses, SDG targets and pages only as `[[kind:id]]` tags.
   Each tag is resolved against the catalogue and shown with its official label; unknown IDs are
   dropped and counted on /about. Numbers not found in the context are flagged.
4. Without a model (or when it fails) `guide.py` answers the common questions from the same
   facts in English, Malay or Chinese.
