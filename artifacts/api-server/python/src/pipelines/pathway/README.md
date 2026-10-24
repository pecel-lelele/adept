# pipelines.pathway (F5, M3)

Course catalogue → `src/data/seed/courses/courses.csv`. The pathway engine recommends **only**
courses in that file.

| Stage | Choice |
|---|---|
| Source | Microsoft Learn Catalog API (public, no key) for curated module / path UIDs; `MANUAL` rows for HRD Corp-claimable courses checked on the provider's page |
| Preprocessing | strip tracking params; minutes → hours |
| Validation | curated UIDs must still exist (fails loudly if retired); skill IDs exist in the taxonomy; level 1-5; https URLs |
| Serving | seed CSV (DB via `make seed`; API reads it directly in mock mode) |

```bash
PYTHONPATH=src/api:src .venv/bin/python -m pipelines.pathway.run
```
