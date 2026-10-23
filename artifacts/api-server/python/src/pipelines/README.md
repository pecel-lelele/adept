# Pipelines

Offline data / ML jobs, one folder per feature. Run from the repo root with the project .venv, e.g. `PYTHONPATH=src .venv/bin/python -m pipelines.trends.run`.

Structure each job as: source → preprocessing/cleaning → features → model/method →
evaluation → serving, and document it in the feature's `FEATURE.md` and `docs/decisions.md`.
Raw downloads go in `src/data/raw/` (gitignored).
