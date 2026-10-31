# src/pipelines/trends (F2, M1)

Weekly trend refresh: ingest → score → validate → publish one dated snapshot.

```bash
PYTHONPATH=src/api:src python -m pipelines.trends.run              # full run
PYTHONPATH=src/api:src python -m pipelines.trends.run --skip-ingest # rescore stored signals
PYTHONPATH=src/api:src python -m pipelines.trends.run --dry-run     # validate, publish nothing
```

The app's automatic refresh is scheduled by `.github/workflows/automatic-data-refresh.yml`;
`trends-refresh.yml` is a manual backup only. That backup requires `TREND_DATABASE_URL`
pointing at a database reachable by the GitHub-hosted runner.
The workflow maps this secret to process `DATABASE_URL`; naming the secret `DATABASE_URL`
alone does not configure it. Replit's development `helium` host cannot be used externally.
Publish Replit to provision its production database, then use its production connection
details. Also configure secret `TRENDS_RUNPOD_API_KEY` and repository variable
`TRENDS_RUNPOD_ENDPOINT_ID=ta14jd0by2ijl2`. No model weights are installed in Actions.

The daily in-app refresh uses a separate scheduler credential. The backup is manually
started through **Actions → Trends refresh → Run workflow** from the reviewed main ref.
Missing settings fail a manual backup run. Preflight checks database connectivity before ingestion or paid inference.
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

## One-time backfill and portable seed (M1-024, M1-027)

`backfill.py` is an operator tool; the API and pages never call it. Run from the repository root
with `PYTHONPATH=src/api:src` and the provider settings for that process only:

1. `python -m pipelines.trends.backfill estimate` prints the range, paper count, arXiv time, cost
   estimate and the resolved target. It makes no network call and no write.
2. `... equivalence --target host:port/db` compares Gemini with MiniLM on the same papers and
   writes `src/data/seed/trends/paper_store/equivalence.json`. The pass bar is in M1-024. MiniLM
   rows come from the database if stored; otherwise the encoder selected by
   `TRENDS_EMBEDDING_BACKEND` (`local` needs no paid call) produces and stores them. An existing
   threshold is reused for the same model; the comparison uses only papers with MiniLM evidence,
   while Gemini storage uses every fully fetched paper in each day. The 500-paper pass bar also
   requires at least 50 shared papers in each of the two recent 7-day windows; the report shows
   both counts. This gate was added before any live equivalence result was recorded.
3. `... run --target host:port/db` stores every missing day from 2026-01-01 in resumable 14-day
   chunks, then publishes the rolling snapshot. Run it again to resume. It refuses to start
   without a passing report. Committing that report is what switches `TRENDS_MATCHER=auto` to
   Gemini.
4. `... export-seed` writes the series to `src/data/seed/trends/paper_store/` from one
   repeatable-read transaction, so a concurrent daily correction cannot mix totals and papers.

To load the history elsewhere, apply migrations and run `make seed` with `DATABASE_URL` set to
that database. No arXiv or model call is made and existing rows are kept.

Stages: arXiv cs.AI submissions → title + abstract → Gemini embeddings (384 dimensions) → cosine
at or above one stored threshold per model → equivalence against MiniLM → per-paper rows counted
by the rolling series.
