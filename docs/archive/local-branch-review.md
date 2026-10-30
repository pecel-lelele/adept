# Local branch review

Inventory on 30 October 2026 against origin/main. Existing merged branches remain intact; no history was rewritten and no duplicate PR is needed for equivalent changes. The detached historical Codex checkout is not a local branch. Untracked proposed handover notes in the two Claude worktrees are preserved locally; their material decisions are recorded in the append-only log.

| Branch | Status | Earlier merged PR |
|---|---|---|
| `chore/core-replit-deploy` | merged/equivalent | — |
| `chore/core-untrack-claude` | merged/equivalent | 11 |
| `chore/skeleton` | merged/equivalent | 1 |
| `docs/core-minilm-endpoint` | merged/equivalent | — |
| `docs/core-readme-cleanup` | merged/equivalent | 14 |
| `docs/core-restore-readme-diagrams` | merged/equivalent | 15 |
| `docs/core-submission-accuracy` | merged/equivalent | 25 |
| `feat/catalogue-roles-skills-courses` | merged/equivalent | 10 |
| `feat/core-adi-assistant` | merged/equivalent | 9 |
| `feat/core-insight-design` | merged/equivalent | 7 |
| `feat/core-m3-workspace-navigation` | merged/equivalent | — |
| `feat/jobs-live-openings` | merged/equivalent | 13 |
| `feat/matching-scoring-engine` | merged/equivalent | 4 |
| `feat/minilm-runpod-deploy` | merged/equivalent | 16 |
| `feat/pathway-sdg-guardrails` | merged/equivalent | 2 |
| `fix/core-backend-perf-security` | merged/equivalent | 8 |
| `fix/core-replit-deployment` | merged/equivalent | 17 |
| `fix/core-replit-next-patch` | merged/equivalent | 19 |
| `fix/core-review-regressions` | active review | — |
| `fix/core-root-layout-restoration` | merged/equivalent | 22 |
| `fix/core-root-replit-deployment` | merged/equivalent | — |
| `fix/core-single-public-server` | merged/equivalent | 24 |
| `main` | merged/equivalent | — |
| `refactor/pathway-trend-and-match-ports` | merged/equivalent | 5 |
| `security/publish-hardening` | merged/equivalent | 20 |
| `worktree-agent-a17103c77ff6e8291` | active review | — |
| `worktree-agent-a30a3ff3fc8019a74` | active review | — |
| `worktree-agent-ab3aa728dfca284ec` | active review | — |
| `worktree-agent-ae781c8985e0fb4d3` | active review | — |

The five active branches form an explicit PR stack: Adi → frontend → trends/jobs → infrastructure → final integration. Review/merge in that order, respecting each PR's checks and draft state. The integration PR contains corrections to earlier drafts and is the acceptance candidate. No production release is implied.
