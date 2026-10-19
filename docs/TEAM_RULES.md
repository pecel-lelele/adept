# Team Rules

How four people work in one repo without getting in each other's way.
These are working agreements, not bureaucracy: if a rule slows you down for no reason, raise it and change it (with a `docs/decisions.md` entry).

---

## 1. The idea in one paragraph

Merge conflicts happen when two people edit the same lines at the same time. We avoid most of them by **organising work by feature**: each feature has an owner and a home in the repo, people mostly work inside their own feature, and the few things everyone shares are changed carefully. Small branches merged often do the rest.

## 2. Features and owners

| Feature | Owner | What it covers |
|---|---|---|
| F1 Skills profile intake | M2 | Questionnaire, CV parsing, skill extraction, skill confirmation |
| F2 AI-trend signal layer | M1 | Trend sources, ingestion, snapshots, Future Skills Radar, admin data pages |
| F3 Scenarios & uncertainty | M1 | Moderate vs fast scenarios, outlook ranges, estimate labels |
| F4 Future-role matching | M2 | Taxonomy, explainable score, skills gap, evaluation, fairness |
| F5 Reskilling pathway | M3 | Course catalogue, ordering, time estimate, progress |
| F6 SDG mapping | M3 | SDG targets, role/skill mapping, contribution views |
| F7 Organisation mode | M4 | HR / career-centre views, heatmap, group plans |
| F8 Guardrails & transparency | M3 | LLM gateway, ID validation, sources, About page |
| Core | M4 | Landing, app shells, shared UI, auth/demo login, integration, deploy, submission |

**Owner** means: you lead it, you decide how it's built, and you review changes others make to it. It doesn't mean nobody else may touch it.

## 3. Where code lives

Organise code **by feature**. The root layout is fixed by the hackathon committee (`docs/`, `src/`, `submission/`, `tests/` plus a few root files; no other top-level folders). The skeleton sets this up, roughly:

```
src/web/src/features/<feature>/       UI for the feature
src/web/src/app/...                   routes; keep page files thin, import from features/
src/web/messages/<locale>/<ns>.json   translations, one file per feature namespace
src/api/app/features/<feature>/       API + logic for the feature
src/api/app/contracts/<feature>.py    shared Pydantic contracts (shared thing, see §4)
src/pipelines/<feature>/              offline data / ML jobs
src/data/seed/<feature>/              synthetic sample data (src/data/raw/ is gitignored)
src/db/migrations/                    timestamped SQL migrations (shared thing, see §4)
tests/api/<feature>/                  API tests for the feature
tests/pipelines/<feature>/            pipeline tests for the feature
submission/                           proposal, pitch deck, demo video link
```

Python dependencies are in the root `requirements.txt`; JS dependencies in `src/web/package.json`.

Guidelines, not laws:

- **Work mostly inside your feature's folders.** Inside them, structure things however suits you.
- **Need to change another feature's code?** Fine. Tell the owner (chat), keep the change small, and ask them to review the PR.
- **New feature or sub-feature?** Create its own folder rather than growing someone else's.

## 4. Shared things (handle with a heads-up)

These affect everyone, so changes need a quick message in the team chat **before** you push, and a line in `docs/decisions.md`:

| Shared thing | Why it matters | How to change it |
|---|---|---|
| API contracts / shared types | Other features read them | Adding a field is easy; renaming/removing needs agreement from affected owners |
| Database migrations | Everyone's database | Add **new** migration files only; never edit an old one |
| Dependencies (`requirements.txt`, `src/web/package.json`, `src/web/pnpm-lock.yaml`) | Lockfile conflicts are painful | Prefer a small separate PR; pull and re-install after it's merged |
| Root config (`Makefile`, `docker-compose.yml`, env vars, `.github/`) | Everyone's environment | Separate small PR; update `.env.example` if you add a variable |
| Navigation / app shell / shared UI components | All pages use them | Coordinate with M4 |
| `docs/PROJECT_CONTEXT.md`, `CLAUDE.md`, `GEMINI.md` | Shared AI context | Team agrees first |

If two people need the same shared change, one person does it and the other waits for the merge.

## 5. Tech stack

**Fixed for everyone (primary stack):**

| Layer | Tech |
|---|---|
| Backend, data, ML | Python |
| Frontend | Next.js (TypeScript) |
| Database | PostgreSQL |
| Version control | Git + GitHub (this repo) |

The skeleton also ships with **starter defaults** (e.g. the web framework for the API, CSS/UI library, migration tool). Use them unless you have a reason not to.

**Everything else is chosen per feature by its owner**: models, libraries, data sources, methods, formulas. See `docs/TASKS.md` for the open choices in each feature. Two conditions:

1. Record the choice in `docs/decisions.md`.
2. If it adds a dependency other features will also install, or replaces a starter default, treat it as a shared change (§4).

## 6. Branches and pull requests

- `main` is the shared branch and must **always run**. Nobody commits to it directly.
- Do each task on a short-lived branch, then open a PR into `main`.
- Branch names: `<type>/<feature>-<short-desc>`, e.g. `feat/matching-score-breakdown`, `fix/trends-empty-response`.
- Types: `feat`, `fix`, `docs`, `chore`, `refactor`.
- One approval before merging, ideally from the owner of any feature you touched. If nobody is free and it only touches your own feature, merge and ask for a review afterwards.
- Keep PRs small enough to review in ~10 minutes. Merge at least every 1–2 days so branches don't drift.

## 7. Daily git routine (copy this)

**Start a task**

```bash
git checkout main
git pull
git checkout -b feat/trends-radar-chart
```

**While working**: commit small and often

```bash
git status                                   # check what you're about to add
git add src/web/src/features/trends/         # add specific paths, not everything blindly
git commit -m "feat(trends): add radar chart"
```

**Before opening a PR**: bring in everyone else's work

```bash
git fetch origin
git rebase origin/main
make check                                   # or whatever check command the skeleton provides
git push -u origin feat/trends-radar-chart
```

Then open the PR on GitHub.

**If the rebase shows a conflict**

1. `git status` lists the conflicted files.
2. Open each one. Keep the correct version (often both changes), delete the `<<<<<<<`, `=======`, `>>>>>>>` markers.
3. `git add <file>` then `git rebase --continue`.
4. Unsure what the other person meant? `git rebase --abort` and ask them. Nothing is lost.

**Avoid**

- `git push --force` on `main`.
- Committing `.env`, secrets, real personal data, or large raw data files.
- Keeping one branch alive for days without merging.

## 8. Commit messages

`<type>(<feature>): <what changed>`, e.g. `feat(sdg): add target-level reasons`, `fix(profile): handle empty CV`.

## 9. Decisions log (required)

**Every change you make gets an entry in `docs/decisions.md`, in the same PR.** That includes tech choices, methods, data sources, formulas, contract or schema changes, new dependencies and notable feature changes. Small fixes can be one line.

- Write only in **your own section** (M1/M2/M3/M4), adding entries at the **bottom** of that section. Separate sections = git can usually merge without conflicts.
- Don't edit old entries; add a new one with `Replaces: <ID>`.
- For data/ML changes, fill in the pipeline line (source → preprocessing → features → model → evaluation → serving). This becomes the methodology section of the proposal.
- Conflict in `decisions.md`? Keep **both** sides, remove the markers, continue.

## 10. Using Claude Code / Gemini CLI

1. Start a session by saying who you are and what you're working on: "I'm M2, working on F4 matching."
2. The assistant works mainly in that feature. Before changing another feature or a shared thing (§4), it tells you and waits for your OK.
3. It adds the `docs/decisions.md` entry for the change.
4. Read the diff (`git diff`) before you commit. You own what you commit.
5. Personal preferences go in `CLAUDE.local.md` or your own Gemini settings (not committed).

## 11. Communication

- Short daily check-in: done yesterday, doing today, blocked by whom.
- Heads-up in chat before shared changes (§4) and before merging anything big.
- Waiting on someone's API? Build against mock data and keep going.

## 12. Done means

- [ ] Works locally and `make check` (or the project's check command) passes
- [ ] Follows the handbook rules: synthetic data only, sources and dates shown, nothing invented, predictions marked as estimates
- [ ] Entry added to `docs/decisions.md`
- [ ] Merged into `main`
