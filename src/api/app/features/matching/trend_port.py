"""Thin adapter: fetches M1's trend snapshot and returns a velocity dict.

The real HTTP call uses ``httpx`` (sync, to match FastAPI's sync service layer).
In tests, inject a fake callable instead of the real ``fetch_velocities``.

**httpx is a new dependency** — announce to the team before adding to
requirements.txt (per TEAM_RULES §Shared Things Protocol).
"""

from __future__ import annotations

from typing import Literal

import httpx

ScenarioId = Literal["moderate", "fast"]

_SNAPSHOT_URL = "/api/v1/trends/snapshot"


def fetch_velocities(
    base_url: str,
    scenario: ScenarioId,
    *,
    timeout: float = 5.0,
) -> dict[str, float]:
    """Call M1's snapshot endpoint and extract per-skill velocity for ``scenario``.

    Returns ``{skill_id: velocity}`` ready to pass into ``scoring.trend_scores()``.
    Returns an empty dict on any HTTP / parse failure (callers fall back to NEUTRAL).
    """
    try:
        resp = httpx.get(
            f"{base_url}{_SNAPSHOT_URL}",
            params={"scenario": scenario},
            timeout=timeout,
        )
        resp.raise_for_status()
        return _parse(resp.json(), scenario)
    except Exception:
        pass

    # In-process fallback: useful during unit tests and when running in a single process
    try:
        from app.features.trends import service as trends_service

        snap = trends_service.get_snapshot(snapshot_date=None, scenario=scenario)
        velocity_key = f"velocity_{scenario}"
        return {
            item.skill_id: float(getattr(item, velocity_key))
            for item in snap.items
            if hasattr(item, velocity_key)
        }
    except Exception:
        return {}


def _parse(data: dict, scenario: ScenarioId) -> dict[str, float]:
    """Extract ``{skill_id: velocity_<scenario>}`` from ``TrendSnapshotResponse``.

    M1's contract (contracts/trends.py):
        TrendSnapshotResponse.items: list[SkillVelocity]
        SkillVelocity fields: skill_id, velocity_moderate, velocity_fast
    """
    velocity_key = f"velocity_{scenario}"
    return {
        row["skill_id"]: float(row[velocity_key])
        for row in data.get("items", [])
        if velocity_key in row
    }
