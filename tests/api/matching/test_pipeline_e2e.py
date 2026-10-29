"""HTTP-level coverage for the saved-profile to explainable-match pipeline."""

from __future__ import annotations

import csv
import time
from datetime import date
from pathlib import Path
from typing import NoReturn
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.features.matching import repository
from app.features.profile import repository as profile_repo


def test_role_interest_tags_are_loaded_from_role_catalogue() -> None:
    """Production role tags must come from the same catalogue as role labels."""
    seed = Path(__file__).resolve().parents[3] / "src" / "data" / "seed" / "taxonomy"
    with (seed / "roles.csv").open(encoding="utf-8", newline="") as file:
        catalogue = {row["id"]: row for row in csv.DictReader(file)}
    with (seed / "role_skills.csv").open(encoding="utf-8", newline="") as file:
        requirements = {}
        for row in csv.DictReader(file):
            requirements.setdefault(row["role_id"], {})[row["skill_id"]] = int(
                row["required_level"]
            )

    for role in repository.load_roles():
        expected = frozenset(
            tag.strip()
            for tag in catalogue[role.role_id]["interest_tags"].split("|")
            if tag.strip()
        )
        assert role.interest_tags == expected
        assert {skill.skill_id: skill.required_level for skill in role.skills} == requirements[
            role.role_id
        ]


def test_saved_profile_to_ranked_match_http_pipeline(client: TestClient) -> None:
    """Save a profile, then check ranking, details, attribution, gaps and SDG badges."""
    user_id = "weijie"
    headers = {"X-Demo-User": user_id}
    previous = profile_repo.get_profile(user_id)
    try:
        profile = client.post(
            "/api/v1/profile",
            headers=headers,
            json={
                "segment": "working",
                "interests": ["data", "analytics"],
                "hours_per_week": 5,
                "budget_myr": 0,
                "hrd_eligible": False,
            },
        )
        assert profile.status_code == 200, profile.text
        saved = client.put(
            "/api/v1/profile/skills/confirm",
            headers=headers,
            json={"skills": [{"skill_id": "python", "level": 2}, {"skill_id": "sql", "level": 2}]},
        )
        assert saved.status_code == 200, saved.text

        response = client.get("/api/v1/matches", headers=headers, params={"scenario": "moderate"})
        assert response.status_code == 200, response.text
        body = response.json()
        matches = body["matches"]
        assert matches
        expected_order = sorted(matches, key=lambda item: (-item["score"], item["role_id"]))
        assert [item["role_id"] for item in matches] == [item["role_id"] for item in expected_order]

        match = next(item for item in matches if item["role_id"] == "data-analyst")
        assert {component["name"] for component in match["components"]} == {
            "skill_overlap",
            "trend_outlook",
            "interest_fit",
        }
        assert match["trend_coverage"] > 0
        assert match["meta"]["snapshot_date"] == "2026-10-20"
        assert match["meta"]["scenario"] == "moderate"
        assert match["meta"]["sources"]
        assert match["meta"]["is_estimate"] is True
        assert any(skill["id"] == "sql" for skill in match["partial_skills"])
        assert match["sdg_targets"]

        # A strict M1 database failure must fail quickly as 503, not hang or use a mock.
        from app.features.matching import trend_port
        from app.features.trends import repository as trend_repository

        error_type = trend_repository.TrendsUnavailableError

        def database_failure(
            snapshot_date: date | None,
            scenario: str,
            strict: bool = False,
            source: str = "db",
        ) -> NoReturn:
            assert strict is True
            assert source == "db"
            raise error_type("test database unavailable")

        started = time.monotonic()
        live_settings = trend_port.get_settings().model_copy(update={"app_env": "production"})
        with (
            patch("app.features.matching.trend_port.get_settings", return_value=live_settings),
            patch("app.features.trends.service.get_snapshot", side_effect=database_failure),
        ):
            unavailable = client.get(
                "/api/v1/matches", headers=headers, params={"scenario": "moderate"}
            )
        assert unavailable.status_code == 503, unavailable.text
        assert unavailable.json()["error"]["code"] == "trend_unavailable"
        assert time.monotonic() - started < 2.5
    finally:
        if previous is None:
            profile_repo._store.pop(user_id, None)
        else:
            profile_repo._store[user_id] = previous
