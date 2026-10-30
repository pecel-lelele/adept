"""F5 pipeline (owner M3): course catalogue → src/data/seed/courses/courses.csv.

The rows are defined in `app.features.pathway.catalogue_sources` (shared with live sync):
Microsoft Learn Catalog API items, free Coursera courses and HRD Corp-claimable provider
courses, each with its source and verification date.

    source        → Microsoft Learn API response (or --from-file) + hand-checked rows
    preprocessing → strip tracking params; minutes → hours (1 decimal)
    validation    → curated UIDs still listed; skill IDs exist; level 1-5; https URLs;
                    every HRD Corp claim quotes the provider
    serving       → courses.csv (DB via `make seed` or live sync; API reads DB or this file)

Run from the repo root:  PYTHONPATH=src/api:src .venv/bin/python -m pipelines.pathway.run
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from app.core.seed import SEED_DIR
from app.features.pathway.catalogue_sources import (
    COURSERA,
    CURATED,
    FREE_MS,
    MANUAL,
    CourseRow,
    all_rows,
    clean_url,
    fetch_mslearn,
    from_mslearn,
    validate,
    write_csv,
)

OUT = SEED_DIR / "courses" / "courses.csv"

__all__ = [
    "COURSERA",
    "CURATED",
    "FREE_MS",
    "MANUAL",
    "CourseRow",
    "clean_url",
    "from_mslearn",
    "known_skills",
    "main",
    "validate",
]


def known_skills(seed: Path = SEED_DIR) -> set[str]:
    with (seed / "taxonomy" / "skills.csv").open(encoding="utf-8") as fh:
        return {row["id"] for row in csv.DictReader(fh)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-file", type=Path, help="read a saved API response instead")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--retrieved", type=date.fromisoformat, default=date.today())
    args = parser.parse_args(argv)
    payload = (
        json.loads(args.from_file.read_text(encoding="utf-8"))
        if args.from_file
        else fetch_mslearn()
    )
    rows = all_rows(payload, args.retrieved)
    validate(rows, known_skills())
    write_csv(rows, args.out)
    print(f"pipelines.pathway: {len(rows)} courses -> {args.out}")


if __name__ == "__main__":
    main()
