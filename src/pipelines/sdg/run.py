"""F6 pipeline (owner M3): official SDG goals and targets → seed CSVs.

Source: UN Statistics Division SDG API, `GET /v1/sdg/Goal/List?includechildren=true`
(public, no key). It returns all 17 goals with their 169 targets and official wording.

    source        → fetch the JSON (or read a saved copy with --from-file)
    preprocessing → keep goal code/title and target code/title; drop indicators and series
    validation    → exactly 17 goals, codes 1..17, every target code starts with its goal
    serving       → src/data/seed/sdg/sdg_goals.csv + sdg_targets.csv (loaded by `make seed`
                    and read directly by the API in mock mode)

Run from the repo root:  PYTHONPATH=src .venv/bin/python -m pipelines.sdg.run
"""

from __future__ import annotations

import argparse
import csv
import json
import ssl
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

API_URL = "https://unstats.un.org/SDGAPI/v1/sdg/Goal/List?includechildren=true"
GOAL_PAGE = "https://sdgs.un.org/goals/goal{n}"
SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed" / "sdg"

# Official short names of the goals (the API only carries the long statement).
# Source: https://sdgs.un.org/goals
SHORT_TITLES: dict[int, str] = {
    1: "No Poverty",
    2: "Zero Hunger",
    3: "Good Health and Well-being",
    4: "Quality Education",
    5: "Gender Equality",
    6: "Clean Water and Sanitation",
    7: "Affordable and Clean Energy",
    8: "Decent Work and Economic Growth",
    9: "Industry, Innovation and Infrastructure",
    10: "Reduced Inequalities",
    11: "Sustainable Cities and Communities",
    12: "Responsible Consumption and Production",
    13: "Climate Action",
    14: "Life Below Water",
    15: "Life on Land",
    16: "Peace, Justice and Strong Institutions",
    17: "Partnerships for the Goals",
}


@dataclass(frozen=True)
class Goal:
    id: int
    title: str
    short_title: str


@dataclass(frozen=True)
class Target:
    id: str
    goal: int
    label: str


def parse(payload: list[dict[str, Any]]) -> tuple[list[Goal], list[Target]]:
    goals: list[Goal] = []
    targets: list[Target] = []
    for item in payload:
        n = int(item["code"])
        goals.append(Goal(n, " ".join(str(item["title"]).split()), SHORT_TITLES[n]))
        for t in item.get("targets", []):
            code = str(t["code"]).strip()
            targets.append(Target(code, n, " ".join(str(t["title"]).split())))
    validate(goals, targets)
    return sorted(goals, key=lambda g: g.id), sorted(targets, key=_target_sort_key)


def _target_sort_key(t: Target) -> tuple[int, int, str]:
    suffix = t.id.split(".", 1)[1]
    return (t.goal, int(suffix) if suffix.isdigit() else 1000, suffix)


def validate(goals: list[Goal], targets: list[Target]) -> None:
    ids = sorted(g.id for g in goals)
    if ids != list(range(1, 18)):
        raise ValueError(f"expected goals 1..17, got {ids}")
    for t in targets:
        if not t.id.startswith(f"{t.goal}.") or not t.label:
            raise ValueError(f"bad target {t}")
    if len({t.id for t in targets}) != len(targets):
        raise ValueError("duplicate target codes")
    missing = {g.id for g in goals} - {t.goal for t in targets}
    if missing:
        raise ValueError(f"goals without targets: {sorted(missing)}")


def fetch(url: str = API_URL, timeout_s: int = 60) -> list[dict[str, Any]]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_s, context=ssl.create_default_context()) as r:
        data: list[dict[str, Any]] = json.load(r)
    return data


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
