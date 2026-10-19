"""Official SDG goals and targets (F6) from the UN Statistics Division SDG API.

Shared by the offline pipeline (`pipelines.sdg.run`, writes the seed CSVs) and live sync
(`app.features.sdg.sync`, writes PostgreSQL), so both always parse the same way.
`GET /v1/sdg/Goal/List?includechildren=true` is public and needs no key.
"""

from __future__ import annotations

import json
import ssl
import urllib.request
from dataclasses import dataclass
from typing import Any

API_URL = "https://unstats.un.org/SDGAPI/v1/sdg/Goal/List?includechildren=true"
GOAL_PAGE = "https://sdgs.un.org/goals/goal{n}"

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
