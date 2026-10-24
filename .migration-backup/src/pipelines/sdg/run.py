"""F6 pipeline (owner M3): official SDG goals and targets → seed CSVs.

Parsing lives in `app.features.sdg.sources` (shared with live sync).

    source        → UN SDG API `Goal/List?includechildren=true` (or --from-file)
    preprocessing → keep goal code/title and target code/title; drop indicators and series
    validation    → exactly 17 goals, codes 1..17, every target code starts with its goal
    serving       → src/data/seed/sdg/sdg_goals.csv + sdg_targets.csv (loaded by `make seed`
                    or live sync; the API reads the DB or these files)

Run from the repo root:  PYTHONPATH=src/api:src .venv/bin/python -m pipelines.sdg.run
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from app.core.seed import SEED_DIR as _SEED_ROOT
from app.features.sdg.sources import (
    GOAL_PAGE,
    SHORT_TITLES,
    Goal,
    Target,
    fetch,
    parse,
    validate,
)

SEED_DIR = _SEED_ROOT / "sdg"

__all__ = ["SHORT_TITLES", "Goal", "Target", "fetch", "main", "parse", "validate", "write"]


def write(goals: list[Goal], targets: list[Target], retrieved: date, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "sdg_goals.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["id", "title", "short_title", "source_url", "retrieved_at"])
        for g in goals:
            w.writerow([g.id, g.title, g.short_title, GOAL_PAGE.format(n=g.id), retrieved])
    with (out / "sdg_targets.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["id", "goal", "label", "source_url", "retrieved_at"])
        for t in targets:
            w.writerow([t.id, t.goal, t.label, GOAL_PAGE.format(n=t.goal), retrieved])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-file", type=Path, help="read a saved API response instead")
    parser.add_argument("--out", type=Path, default=SEED_DIR)
    parser.add_argument("--retrieved", type=date.fromisoformat, default=date.today())
    args = parser.parse_args(argv)
    payload = json.loads(args.from_file.read_text(encoding="utf-8")) if args.from_file else fetch()
    goals, targets = parse(payload)
    write(goals, targets, args.retrieved, args.out)
    print(f"pipelines.sdg: {len(goals)} goals, {len(targets)} targets -> {args.out}")


if __name__ == "__main__":
    main()
