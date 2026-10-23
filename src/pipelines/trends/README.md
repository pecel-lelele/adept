# src/pipelines/trends (F2, M1)

Weekly trend refresh: ingest → score → validate → publish one dated snapshot.

```bash
PYTHONPATH=src/api:src python -m pipelines.trends.run              # full run
PYTHONPATH=src/api:src python -m pipelines.trends.run --skip-ingest # rescore stored signals
PYTHONPATH=src/api:src python -m pipelines.trends.run --dry-run     # validate, publish nothing
```

Scheduled by `.github/workflows/trends-refresh.yml` (Mondays) when the `TREND_DATABASE_URL`
repository secret points at a production database reachable by the GitHub-hosted runner.
The workflow maps this secret to process `DATABASE_URL`; naming the secret `DATABASE_URL`
alone does not configure it. Replit's development `helium` host cannot be used externally.
Publish Replit to provision its production database, then use its production connection
details. Also configure secret `TRENDS_RUNPOD_API_KEY` and repository variable
`TRENDS_RUNPOD_ENDPOINT_ID=ta14jd0by2ijl2`. No model weights are installed in Actions.

The schedule is Mondays 03:41 UTC (11:41 WITA), with manual dispatch through
**Actions → Trends refresh → Run workflow**. Missing settings skip work and can leave a
green run. Preflight checks database connectivity before ingestion or paid inference.
Require the actual `Published snapshot YYYY-MM-DD.` log and verify the date in the app.
A live inference test passed on 24 October 2026; the first integrated refresh fetched 366
papers but failed saving to private host `helium`. Inference readiness does not establish
publication. See [deployment evidence and recovery](runpod/DEPLOYMENT_HANDOFF.md).

MiniLM runs on a RunPod Serverless worker for background ingestion, with the same
scoring and publication rules. Build, endpoint configuration and environment variables
are in [`runpod/README.md`](runpod/README.md). Explicitly select
`TRENDS_EMBEDDING_BACKEND=local` for local CPU development.

| Stage | Choice |
|---|---|
| Source | arXiv cs.AI listing (`arxiv_ingest.py`); BLS 2023-2033 projections as labour baseline (`labor_baseline.py`) |
| Preprocessing / cleaning | HTML stripped, abstracts split into sentences; raw pull cached per day |
| Features | Sentence-level cosine match (all-MiniLM-L6-v2, threshold 0.55) → mention counts per skill per ISO week |
| Model / method | `score.score_rows`: log-ratio research velocity t1 vs t0, 0.6 × velocity + 0.4 × labour decay, fast-scenario transform by automation exposure |
| Evaluation | `run.validate`: two distinct weeks, ≥ 50 skills, taxonomy ids only, finite numbers, known direction labels; failed runs publish nothing |
| Serving | `trend_snapshots` + `trend_snapshot_meta` in one transaction; the note names the measured week, read back as `observed_from` / `observed_to` |

`populate_dual_snapshot.py` and `export_fixtures_from_db.py` build the historical demo
snapshots (October 2024 arXiv windows replayed as 2026 dates; the app labels them as such).
