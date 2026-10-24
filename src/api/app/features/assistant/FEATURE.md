# Adi, the Adept assistant (Core, M4; guardrails F8)

- **API**: `POST /api/v1/assistant/chat` (signed-in learner or manager only).
- **Contracts**: `src/api/app/contracts/assistant.py`
- **Web**: `src/web/src/components/adi/` (mascot, 3D mascot, chat panel), route handler
  `src/web/src/app/api/assistant/route.ts`.

## How an answer is made

1. `context.py` gathers the person's own profile, matches, saved plan and its scenario's
   effective progress, team gaps and dated trends. Rejected completions never count as done.
2. `guide.py` renders candidate answer blocks in English, Malay or Chinese from those facts.
3. The model selects one or two block IDs through the F8 gateway and `validate_ids`.
   Every prompt component is sanitised and PII-redacted. Model prose, rationale, names and
   figures are never displayed. References in the selected server-authored blocks resolve
   against the actual catalogue before rendering.
4. Missing model, invalid selection or provider failure uses the deterministic guide. Provider
   retries use cancellable async I/O under one wall-clock budget; the complete API answer has
   a 24-second deadline and at most four outstanding workers. Expired context cannot start
   paid work. Attribution records the model that actually answered in that request.
5. Adi appears only in signed-in workspaces. Account changes remount the conversation, abort
   in-flight browser requests and remove other accounts' stored chats.

## Saved-plan answers and intent coverage

Progress, study duration and cost have separate server-authored blocks. Their numeric fields
come from the saved plan and its scenario's effective progress, and personal-plan replies
carry that saved plan's metadata. Model-enabled and offline answers use the same templates.
An explicit personal-plan question cannot be replaced by a generic model-selected block;
missing plan/progress data is stated, never filled with zero or a guessed figure. Funding and
prices remain estimates requiring current provider and employer confirmation.

English keywords explicitly include ordinary plurals and supported match/learn inflections,
with complete-word boundaries preserved. Chinese remains substring-matched; Malay and Chinese
personal-plan cues are covered by regressions alongside the existing privacy-word exclusions.
