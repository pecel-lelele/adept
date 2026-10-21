"""PR #4 review checks that exercise the production adapters and harness boundary."""

from __future__ import annotations

import ast
import csv
import datetime
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType

import httpx
import pytest
from fastapi.testclient import TestClient

from app.contracts.profile import UserSkill
from app.features.matching import personas, repository, service
from app.features.profile import repository as profile_repository

ROOT = Path(__file__).resolve().parents[3]


def test_matching_contains_no_lru_cache() -> None:
    hits = []
    for path in (ROOT / "src/api/app/features/matching").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                if any(alias.name == "lru_cache" for alias in node.names):
                    hits.append(f"{path.name}:{node.lineno}")
    assert not hits, f"Matching still imports lru_cache: {hits}"


def test_real_trend_port_works_with_http_clients_disabled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the real matching port; only M1's reader is replaced by conftest."""

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Outbound HTTP attempted during matching")

    requests = ModuleType("requests")
    for name in ("get", "post", "request", "Session"):
        monkeypatch.setattr(requests, name, forbidden, raising=False)
    monkeypatch.setitem(sys.modules, "requests", requests)
    for name in ("get", "post", "request", "Client", "AsyncClient"):
        monkeypatch.setattr(httpx, name, forbidden)
    response = client.get("/api/v1/matches")
    assert response.status_code == 200, response.text
    assert response.json()["matches"]


def test_thirty_requests_through_real_trend_port(client: TestClient) -> None:
    with ThreadPoolExecutor(max_workers=30) as pool:
        responses = list(pool.map(lambda _: client.get("/api/v1/matches"), range(30)))
    codes = [response.status_code for response in responses]
    print(f"real trend port concurrency: {len(codes)} responses; statuses={set(codes)}")
    assert codes == [200] * 30


def test_saved_demographic_swaps_leave_matching_identical(client: TestClient) -> None:
    """Synthetic extra attributes must never enter the production match profile."""
    saved = {key: value.model_copy(deep=True) for key, value in profile_repository._store.items()}
    try:
        profile = profile_repository.get_profile("aisyah")
        assert profile is not None
        outputs = []
        for age, gender in [(22, "synthetic-female"), (41, "synthetic-male")]:
            profile_repository.save_profile(
                profile.model_copy(update={"age": age, "gender": gender})
            )
            response = client.get("/api/v1/matches", headers={"X-Demo-User": "aisyah"})
            assert response.status_code == 200, response.text
            outputs.append(response.json())
        assert outputs[0] == outputs[1]
    finally:
        profile_repository._store.clear()
        profile_repository._store.update(saved)


def test_snapshot_meta_with_frozen_today(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.contracts.common import Source
    from app.features.matching.trend_port import TrendSnapshot

    snap = TrendSnapshot(
        velocities={"python": 0.8},
        snapshot_date=datetime.date(2026, 10, 20),
        sources=[
            Source(
                name="Test snapshot",
                url="https://example.com/snapshot",
                retrieved_at=datetime.date(2026, 10, 20),
            )
        ],
        scenario="fast",
        is_estimate=False,
    )

    class FrozenDate(datetime.date):
        @classmethod
        def today(cls) -> FrozenDate:
            return cls(2026, 10, 21)

    monkeypatch.setattr(datetime, "date", FrozenDate)
    monkeypatch.setattr(service, "date", FrozenDate, raising=False)
    monkeypatch.setattr(repository, "date", FrozenDate, raising=False)
    monkeypatch.setattr(service, "fetch_snapshot", lambda scenario: snap)
    assert datetime.date.today().isoformat() == "2026-10-21"
    response = client.get("/api/v1/matches?scenario=fast")
    assert response.status_code == 200, response.text
    expected = {
        "snapshot_date": "2026-10-20",
        "scenario": "fast",
        "is_estimate": False,
        "sources": [source.model_dump(mode="json") for source in snap.sources],
    }
    assert response.json()["meta"] == expected
    assert all(match["meta"] == expected for match in response.json()["matches"])


@pytest.mark.parametrize("user_id", ["aisyah", "weijie", "ravi"])
def test_benchmark_profile_uses_production_skill_scale(user_id: str) -> None:
    """The same seed facts must have identical values in production and evaluation."""
    saved = {key: value.model_copy(deep=True) for key, value in profile_repository._store.items()}
    try:
        profile = profile_repository.get_profile(user_id)
        assert profile is not None
        with (ROOT / "src/data/seed/personas/user_skills.csv").open(encoding="utf-8") as fh:
            skills = [
                UserSkill(skill_id=row["skill_id"], level=int(row["level"]), source=row["source"])
                for row in csv.DictReader(fh)
                if row["user_id"] == user_id
            ]
        harness = personas.load_persona_profile(user_id)
        assert harness is not None
        profile_repository.save_profile(
            profile.model_copy(
                update={
                    "skills": skills,
                    "interests": sorted(harness.interests),
                }
            )
        )
        production = repository._load_profile(user_id)
        assert harness == production, f"{user_id}: benchmark and production use different scales"
    finally:
        profile_repository._store.clear()
        profile_repository._store.update(saved)
