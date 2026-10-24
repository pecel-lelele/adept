"""Mock snapshot fixture for the TrendSnapshotResponse contract.

Loaded from src/data/seed/mock_trends.json at import time (no network call,
no DB dependency). Wire this into repository.py so the endpoint is callable
before live pipeline data is available.

Both scenario variants are generated here:
  - moderate: loaded verbatim from the JSON (meta.scenario already = "moderate")
  - fast:     meta.scenario replaced, each item's velocity_fast and
              direction_fast promoted to the moderate fields so the frontend
              ScenarioToggle sees visibly different results.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.contracts.trends import (
    SkillVelocity,
    TrendSnapshotMeta,
    TrendSnapshotResponse,
)
from app.features.trends.provenance import observation_window

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SEED_DIR = _REPO_ROOT / "src" / "data" / "seed"
_MOCK_FILE = _SEED_DIR / "mock_trends.json"
_MOCK_FILES_BY_DATE: dict[date, Path] = {
    date(2026, 10, 13): _SEED_DIR / "mock_trends_2026-10-13.json",
    date(2026, 10, 20): _SEED_DIR / "mock_trends_2026-10-20.json",
}
AVAILABLE_MOCK_DATES: list[date] = list(_MOCK_FILES_BY_DATE)


def _load_raw(snapshot_date: date | None = None) -> dict:
    dated_file = _MOCK_FILES_BY_DATE.get(snapshot_date)
    if dated_file is not None and dated_file.is_file():
        with dated_file.open(encoding="utf-8") as fh:
            return json.load(fh)
    with _MOCK_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def _parse_meta(raw_meta: dict, scenario: str) -> TrendSnapshotMeta:
    from app.contracts.trends import SourceRef

    window = observation_window(raw_meta, raw_meta.get("data_provenance_note"))
    return TrendSnapshotMeta(
        sources=[
            SourceRef(
                name=s["name"],
                url=s["url"],
                retrieved_at=date.fromisoformat(s["retrieved_at"]),
            )
            for s in raw_meta["sources"]
        ],
        snapshot_date=date.fromisoformat(raw_meta["snapshot_date"]),
        scenario=scenario,  # type: ignore[arg-type]
        is_estimate=raw_meta.get("is_estimate", True),
        weights=raw_meta.get("weights", {"research_velocity": 0.6, "labor_decay": 0.4}),
        labor_decay_is_static=raw_meta.get("labor_decay_is_static", True),
        available_snapshots=[
            date.fromisoformat(d) for d in raw_meta.get("available_snapshots", [])
        ],
        data_provenance_note=raw_meta.get("data_provenance_note"),
        observed_from=window[0],
        observed_to=window[1],
    )


def _parse_items(raw_items: list[dict], scenario: str) -> list[SkillVelocity]:
    from app.core import seed

    labels = {row["id"]: row["label"] for row in seed.rows("taxonomy", "skills")}
    items = []
    for item in raw_items:
        items.append(
            SkillVelocity(
                skill_id=item["skill_id"],
                skill_label=labels.get(item["skill_id"], item["skill_label"]),
                research_velocity=item["research_velocity"],
                labor_decay=item["labor_decay"],
                labor_decay_source_note=item["labor_decay_source_note"],
                automation_exposure=item["automation_exposure"],
                velocity_moderate=item["velocity_moderate"],
                velocity_fast=item["velocity_fast"],
                direction_moderate=item["direction_moderate"],  # type: ignore[arg-type]
                direction_fast=item["direction_fast"],  # type: ignore[arg-type]
            )
        )
    return items


def snapshot(scenario: str, snapshot_date: date | None = None) -> TrendSnapshotResponse:
    """Return a mock TrendSnapshotResponse for the given scenario and date."""
    if snapshot_date is None:
        snapshot_date = AVAILABLE_MOCK_DATES[-1]

    raw = _load_raw(snapshot_date)
    meta = _parse_meta(raw["meta"], scenario)
    meta.available_snapshots = list(AVAILABLE_MOCK_DATES)
    meta.snapshot_date = snapshot_date
    items = _parse_items(raw["items"], scenario)
    return TrendSnapshotResponse(meta=meta, items=items)
