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
