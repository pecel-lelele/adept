# Adi, the Adept assistant (Core, M4; guardrails F8)

- **API**: `POST /api/v1/assistant/chat` (signed-in learner or manager only).
- **Contracts**: `src/api/app/contracts/assistant.py`
- **Web**: `src/web/src/components/adi/` (mascot, 3D mascot, chat panel), route handler
  `src/web/src/app/api/assistant/route.ts`.

## How an answer is made

1. `context.py` gathers the person's own profile, matches, saved plan and its scenario's
   effective progress, team gaps and dated trends. Rejected completions never count as done.
2. `guide.py` renders candidate answer blocks in English, Malay or Chinese from those facts.
3. `guide.intents` routes the question to one block, or two when the runner-up intent is a
   near tie. People-decision requests (hire/fire/promote/admit/reject a person), injection
   and other people's data are refused first; ordinary questions such as "Which roles are
   hiring?" or "admission requirements" are not decisions. The model selects one or two
   block IDs through `select_ids_or_fallback` (F8 gateway, `validate_ids`); a specific
   question's selection must include the routed block.
   Every prompt component is sanitised and PII-redacted. Model prose, rationale, names and
   figures are never displayed. References in the selected server-authored blocks resolve
   against the actual catalogue before rendering.
4. Missing model, invalid selection or provider failure uses the deterministic guide. Provider
   retries use cancellable async I/O under one wall-clock budget; the complete API answer has
   a 24-second deadline, at most four outstanding workers and at most one answer in flight per
   account. Busy, overloaded, timeout and catalogue failures each have their own message.
   Expired context cannot start paid work. Attribution records the model that actually
   answered in that request.
5. Replies follow the question's language when it is clearly Chinese or Malay; otherwise the
   UI locale. Follow-up chips depend on the answer just given, and every chip routes back to
   its own grounded block. At most three chips are returned (`suggestion_ids` are catalogue
   chip IDs, `suggestions` their question text); a chip never repeats the question just asked
   or the answer just shown.
6. Tone: blocks are short, warm and second person. Off-topic questions and requests to make
   up jobs, courses or figures get a friendly refusal (no context, no model); unmatched
   questions get an "unknown" reply that a configured model may replace with a better checked
   block; greetings and thanks get small-talk blocks. After refusals and small talk the chips
   follow the page the person is on.
7. Adi appears only in signed-in workspaces. Account changes remount the conversation, abort
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
