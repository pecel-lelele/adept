"""Skills, roles and categories over a stored range: rebase, projection and attribution (M1-025)."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import REPO_ROOT
from app.features.data_refresh import trend_store
from app.features.trends import comparison, series
from pipelines.trends import score

D0 = date(2026, 1, 1)
LAST = D0 + timedelta(days=299)
TAXONOMY = REPO_ROOT / "src" / "data" / "seed" / "taxonomy"


def _csv(name: str) -> list[dict[str, str]]:
    with (TAXONOMY / name).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_each_role_has_exactly_one_reviewed_category() -> None:
    roles = [r["id"] for r in _csv("roles.csv")]
    rows = _csv("role_categories.csv")
    assert sorted(r["role_id"] for r in rows) == sorted(roles)
    labels: dict[str, set[str]] = {}
    for row in rows:
        labels.setdefault(row["category_id"], set()).add(row["category_label"])
    assert all(len(v) == 1 for v in labels.values()), "one label per category"


def test_role_score_is_importance_weighted_and_empty_if_any_skill_is() -> None:
    shares = {"a": [0.2, 0.2, None], "b": [0.1, None, 0.1]}
    assert comparison.weighted_line(shares, {"a": 1.0, "b": 0.5}) == [
        pytest.approx((0.2 + 0.05) / 1.5, abs=1e-6),
        None,
        None,
    ]


def test_category_is_the_equal_weight_mean_of_its_roles() -> None:
    assert comparison.mean_line([[0.2, None], [0.4, 0.1]]) == [pytest.approx(0.3), None]


def test_rebase_uses_the_first_date_where_every_line_is_above_zero() -> None:
    assert comparison.rebase_index([[0.2, 0.3], [0.1, 0.1]]) == 0
    assert comparison.rebase_index([[0.0, 0.3], [None, 0.1]]) == 1
    assert comparison.rebase_index([[0.0, 0.0], [0.1, 0.1]]) is None


def test_projection_reuses_the_radar_scenarios_and_stays_a_possible_share() -> None:
    velocities = comparison.scenario_velocities(0.1, 0.2, -0.1, 0.5)
    raw = score.composite_velocity(score.research_velocity(0.1, 0.2), -0.1)
    assert velocities["moderate"] == score.scenario_moderate(raw)
    assert velocities["fast"] == score.scenario_fast(raw, 0.5)
    assert comparison.project(0.2, 0.5, 7) == pytest.approx(0.3)
    assert comparison.project(0.2, -2.0, 365) == 0.0
    assert comparison.project(0.5, 2.0, 365) == 1.0


def test_long_ranges_are_weekly_counted_back_from_the_last_day() -> None:
    assert comparison.sampled_indexes(120) == list(range(120))
    weekly = comparison.sampled_indexes(300)
    assert weekly[0] == 0 and weekly[-1] == 299
    assert {b - a for a, b in zip(weekly[1:], weekly[2:], strict=False)} == {7}
    assert 0 < weekly[1] - weekly[0] <= 7
    assert comparison.sampled_indexes(180)[0] == 0
    assert comparison.horizon_days(90)[-1] == 90
    assert comparison.horizon_days(365)[-1] == 365


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    days = [D0 + timedelta(days=i) for i in range(300)]
    calls: dict[str, Any] = {"daily": 0}

    def daily(start: date, end: date, skill_ids: Any) -> Any:
        calls["daily"] += 1
        papers = {d: 50 for d in days if start <= d <= end}
        mentions: dict[tuple[date, str], int] = {}
        for i, d in enumerate(days):
            if start <= d <= end:
                for sid in skill_ids:
                    mentions[(d, sid)] = 5 + (i // 30) if sid != "sql" else max(0, 20 - i // 30)
        return papers, mentions

    monkeypatch.setattr(
        trend_store, "stored_range", lambda: (days[0], days[-1], date(2026, 10, 30))
    )
    monkeypatch.setattr(trend_store, "daily", daily)
    return calls


COMPARE = "/api/v1/trends/compare"


def test_the_whole_stored_year_works_for_role_vs_category(
    client: TestClient, stored: dict[str, Any]
) -> None:
    body = client.get(
        COMPARE,
        params={
            "start": "2026-01-07",
            "end": LAST.isoformat(),
            "entities": ["role:data-analyst", "category:data-science-analytics"],
        },
    ).json()
    assert [line["entity"] for line in body["lines"]] == [
        "role:data-analyst",
        "category:data-science-analytics",
    ]
    assert body["step_days"] == 7 and body["mode"] == "indexed"
    assert body["base_date"] == "2026-01-07"
    assert body["lines"][0]["points"][-1]["day"] == LAST.isoformat()
    assert any(o["entity"] == "role:machine-learning-engineer" for o in body["options"])
    # Rebased to 100 at the base date.
    assert body["lines"][0]["start_value"] == 100.0
    assert body["lines"][0]["points"][0] == {"day": "2026-01-07", "value": 100.0}


def test_every_plottable_role_and_category_can_be_charted(
    client: TestClient, stored: dict[str, Any]
) -> None:
    options = client.get(COMPARE).json()["options"]
    roles = [o["entity"] for o in options if o["kind"] == "role"]
    categories = [o["entity"] for o in options if o["kind"] == "category"]
    assert len(roles) == 47 and len(categories) == 8
    assert "role:production-workers-all-other" not in roles  # no skill profile, so no line
    for entity in roles + categories:
        body = client.get(COMPARE, params={"entities": [entity], "preset": "1M"}).json()
        assert body["lines"] and body["lines"][0]["end_value"] is not None, entity


def test_observed_and_projected_parts_have_separate_attribution(
    client: TestClient, stored: dict[str, Any]
) -> None:
    body = client.get(
        COMPARE, params={"entities": ["skill:python"], "scenario": "fast", "horizon_days": 30}
    ).json()
    observed, projected = body["meta"], body["projection_meta"]
    assert observed["is_estimate"] is False and projected["is_estimate"] is True
    assert observed["scenario"] == projected["scenario"] == "fast"
    # The data snapshot, never the request date.
    assert projected["snapshot_date"] == LAST.isoformat() == observed["snapshot_date"]
    assert {s["name"] for s in projected["sources"]} >= {"arXiv cs.AI submission API"}
    assert any("BLS" in s["name"] for s in projected["sources"])
    assert all(s["url"].startswith("https://") for s in projected["sources"])
    assert observed["sources"][0]["retrieved_at"] == "2026-10-30"
    line = body["lines"][0]
    assert line["moderate_end"] is not None and line["fast_end"] is not None
    assert line["projection"][-1]["day"] == (LAST + timedelta(days=30)).isoformat()
    assert body["projected_from"] == LAST.isoformat()
    assert all(p["value"] >= 0 for p in line["projection"])


def test_a_role_or_category_score_is_labelled_an_estimate(
    client: TestClient, stored: dict[str, Any]
) -> None:
    body = client.get(COMPARE, params={"entities": ["role:data-analyst"]}).json()
    assert body["meta"]["is_estimate"] is True


def test_no_common_base_falls_back_to_raw_and_says_so(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    days = [D0 + timedelta(days=i) for i in range(30)]
    monkeypatch.setattr(trend_store, "stored_range", lambda: (days[0], days[-1], days[-1]))
    monkeypatch.setattr(trend_store, "daily", lambda start, end, ids: ({d: 50 for d in days}, {}))
    body = client.get(COMPARE, params={"entities": ["skill:python"]}).json()
    assert body["mode"] == "raw" and body["raw_fallback"] is True and body["base_date"] is None


def test_raw_mode_returns_shares_without_a_base(client: TestClient, stored: dict[str, Any]) -> None:
    body = client.get(COMPARE, params={"entities": ["skill:python"], "mode": "raw"}).json()
    assert body["mode"] == "raw" and body["raw_fallback"] is False
    assert 0 < body["lines"][0]["end_value"] <= 1


def test_presets_stay_inside_stored_data(client: TestClient, stored: dict[str, Any]) -> None:
    body = client.get(COMPARE, params={"preset": "1W", "entities": ["skill:python"]}).json()
    assert body["start"] == (LAST - timedelta(days=6)).isoformat() and body["end"] == str(LAST)
    assert client.get(COMPARE, params={"preset": "6M"}).json()["step_days"] == 7


@pytest.mark.parametrize(
    "params",
    [
        {"start": "2025-12-01", "end": "2026-02-01"},  # before stored data
        {"start": "2026-02-01", "end": "2026-12-01"},  # after stored data
        {"start": "2026-03-01", "end": "2026-02-01"},
        {"end": "0001-01-01", "preset": "6M"},  # reject before preset subtraction
        {"entities": ["role:not-a-role"]},
        {"entities": [f"skill:s{i}" for i in range(9)]},
        {"entities": ["skill:python", "role:data-analyst"]},
        {"horizon_days": 366},
        {"horizon_days": 0},
    ],
)
def test_bad_choices_are_refused(
    client: TestClient, stored: dict[str, Any], params: dict[str, Any]
) -> None:
    assert client.get(COMPARE, params=params).status_code == 422


def test_empty_store_shows_no_invented_history(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(trend_store, "stored_range", lambda: None)
    monkeypatch.setattr(trend_store, "daily", lambda *a: pytest.fail("no store to read"))
    body = client.get(COMPARE).json()
    assert body["lines"] == [] and body["available_to"] is None
    assert body["projection_meta"] is None
    assert body["meta"]["sources"][0]["url"] == series.EMPTY_SOURCE.url
    assert body["meta"]["observed_from"] is None


@pytest.mark.parametrize(
    "params",
    [
        {"start": "0001-01-01", "end": "9999-12-31"},
        {"start": "2025-01-01", "end": "2026-01-02"},
        {"start": "2026-02-01", "end": "2026-01-01"},
    ],
)
def test_empty_store_rejects_unbounded_or_reversed_ranges(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, params: dict[str, str]
) -> None:
    monkeypatch.setattr(trend_store, "stored_range", lambda: None)
    monkeypatch.setattr(trend_store, "daily", lambda *a: pytest.fail("no store to read"))
    assert client.get(COMPARE, params=params).status_code == 422


def test_180_day_series_includes_the_reported_baseline(
    client: TestClient, stored: dict[str, Any]
) -> None:
    body = client.get(
        COMPARE, params={"start": "2026-01-07", "end": "2026-07-05", "entities": ["skill:python"]}
    ).json()
    line = body["lines"][0]
    assert body["mode"] == "indexed" and body["base_date"] == "2026-01-07"
    assert line["points"][0] == {"day": body["base_date"], "value": line["start_value"]}
    assert line["points"][-1]["day"] == body["end"]


def test_movers_lead_with_risers_then_fallers(client: TestClient, stored: dict[str, Any]) -> None:
    body = client.get(COMPARE, params={"kind": "skill", "preset": "6M", "mode": "raw"}).json()
    changes = [line["change"] for line in body["lines"]]
    assert changes and len(changes) <= 6
    rising = [c for c in changes if c > 0]
    assert changes[: len(rising)] == rising


def test_chart_reads_make_no_network_or_model_call(
    client: TestClient, stored: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core import embeddings
    from app.features.data_refresh import automatic_trends

    monkeypatch.setattr(embeddings, "embed", lambda *a, **k: pytest.fail("model call"))
    monkeypatch.setattr(automatic_trends, "fetch_window", lambda *a, **k: pytest.fail("network"))
    assert client.get(COMPARE, params={"kind": "category"}).status_code == 200
    assert stored["daily"] == 1
