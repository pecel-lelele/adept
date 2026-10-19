# pipelines.sdg (F6, M3)

Official SDG goals and targets → `src/data/seed/sdg/sdg_goals.csv`, `sdg_targets.csv`.

| Stage | Choice |
|---|---|
| Source | UN Statistics Division SDG API `GET /v1/sdg/Goal/List?includechildren=true` (public, no key) |
| Preprocessing | keep goal and target codes and official titles; drop indicators/series; normalise whitespace |
| Validation | exactly goals 1..17; target codes prefixed by their goal; no duplicates; every goal has targets |
| Serving | seed CSVs (DB via `make seed`; read directly by the API in mock mode) |

```bash
PYTHONPATH=src .venv/bin/python -m pipelines.sdg.run                  # live API
PYTHONPATH=src .venv/bin/python -m pipelines.sdg.run --from-file x.json   # saved response
```
