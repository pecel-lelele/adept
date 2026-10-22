# src/pipelines/trends (F2, M1)

Weekly trend refresh: ingest → score → validate → publish one dated snapshot.

```bash
PYTHONPATH=src/api:src python -m pipelines.trends.run              # full run
PYTHONPATH=src/api:src python -m pipelines.trends.run --skip-ingest # rescore stored signals
PYTHONPATH=src/api:src python -m pipelines.trends.run --dry-run     # validate, publish nothing
```

Scheduled by `.github/workflows/trends-refresh.yml` (Mondays) when the `TREND_DATABASE_URL`
secret points at the deployed database. Ingestion needs `sentence-transformers` (installed by
the workflow, CPU-only).

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
