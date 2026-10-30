"""tests/pipelines/trends/test_mock_fixture_consistency.py

Enforces:
1. Mathematical formula consistency between committed mock fixtures and score.py pure functions.
2. Verifiable faithful export: fixtures in src/data/seed/ match the actual rows in PostgreSQL
   trend_snapshots table for both snapshot dates (when DB is available).
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from pipelines.trends.score import direction, scenario_fast


@pytest.fixture
def provenance_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request: pytest.FixtureRequest):  # type: ignore[no-untyped-def]
    """An explicit disposable database, with a separate migrated schema for each test.

    The normal suite never borrows DATABASE_URL/.env. CI's existing database job
    already runs this module with ADEPT_TEST_DATABASE_URL against its pgvector service.
    """
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from psycopg.rows import dict_row

    from app.features.trends import repository, service
    from db import migrate, seed

    url = os.environ.get("ADEPT_TREND_TEST_DATABASE_URL") or os.environ.get(
        "ADEPT_TEST_DATABASE_URL"
    )
    if not url:
        pytest.skip("Explicit disposable trend provenance database not configured")
    schema = "trend_provenance_" + uuid4().hex
    isolated_url = make_conninfo(url, options=f"-c search_path={schema},public")
    with psycopg.connect(url, autocommit=True) as control:
        control.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            with psycopg.connect(isolated_url, autocommit=True) as conn:
                # Apply the actual trend migrations, excluding only the unrelated
                # embedding table: these persistence tests require PostgreSQL, not
                # model embeddings or pgvector. No trend DDL is copied or mocked.
                for name in (
                    "20261020160000_m1_trends_signal_tables.sql",
                    "20261021140000_m1_signal_aggregation_by_fetch_date.sql",
                    "20261022120000_core_trend_snapshot_meta.sql",
                    "20261030120000_trend_replay_provenance.sql",
                ):
                    if (
                        name == "20261030120000_trend_replay_provenance.sql"
                        and getattr(request, "param", None) == "legacy"
                    ):
                        continue
                    body = migrate.up_section(
                        (migrate.MIGRATIONS / name).read_text(encoding="utf-8")
                    )
                    body = re.sub(
                        r"CREATE TABLE IF NOT EXISTS skill_embeddings \(.*?\);",
                        "",
                        body,
                        flags=re.S,
                    )
                    conn.execute(body)
            monkeypatch.setattr(seed, "SEED", tmp_path)
            monkeypatch.setattr(
                repository,
                "_get_connection",
                lambda **_: psycopg.connect(isolated_url, row_factory=dict_row, autocommit=True),
            )
            repository._reset_db_cache()
            service.clear_cache()
            yield isolated_url, tmp_path
        finally:
            service.clear_cache()
            repository._reset_db_cache()
            control.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def _replay_export(path: Path) -> dict:
    """Use actual catalogue rows; change only explicit provenance for this fixture."""
    export = json.loads((SEED_DIR / "mock_trends_2026-10-20.json").read_text(encoding="utf-8"))
    export["meta"].update(
        is_replay=True,
        observation_window_start="2024-10-13",
        observation_window_end="2024-10-19",
        retrieved_at="2026-10-24",
        retrieved_at_basis="git_commit_date",
        retrieval_evidence="git:8a5a4608c0a5907d85e5acf1b8fc246661bbfd2a",
    )
    path.write_text(json.dumps(export), encoding="utf-8")
    return export


def test_replay_fixture_survives_seed_postgres_repository_round_trip(provenance_db) -> None:  # type: ignore[no-untyped-def]
    import psycopg

    from app.features.trends import repository
    from db import seed
    from pipelines.trends.export_fixtures_from_db import export_snapshot

    url, directory = provenance_db
    _replay_export(directory / "mock_trends_2026-10-20.json")
    with psycopg.connect(url) as conn:
        seed.load_trend_exports(conn)
        seed.load_trend_exports(conn)  # provenance import must also be idempotent
        row = conn.execute(
            "SELECT is_replay, observation_window_start, observation_window_end, "
            "retrieved_at, retrieved_at_basis FROM trend_snapshots LIMIT 1"
        ).fetchone()
        assert row == (
            True,
            date(2024, 10, 13),
            date(2024, 10, 19),
            date(2026, 10, 24),
            "git_commit_date",
        )
    snapshot = repository.get_snapshot(date(2026, 10, 20), "moderate", strict=True)
    assert snapshot.meta.served_from == "db"
    assert snapshot.meta.is_fallback is False
    assert snapshot.meta.is_replay is True
    assert snapshot.meta.observation_window_start == date(2024, 10, 13)
    assert snapshot.meta.observation_window_end == date(2024, 10, 19)
    assert snapshot.meta.retrieved_at == date(2026, 10, 24)
    with repository._get_connection() as conn:
        exported = export_snapshot(conn, "2026-10-20", {})
    assert exported["meta"]["is_replay"] is True
    assert exported["meta"]["retrieved_at"] == "2026-10-24"
    assert exported["meta"]["observation_window_end"] == "2024-10-19"


def test_freshness_exposes_same_replay_provenance_from_fixture_and_database(
    provenance_db,
    client,
    monkeypatch: pytest.MonkeyPatch,  # type: ignore[no-untyped-def]
) -> None:
    import psycopg

    from app.features.trends import repository, service
    from db import seed

    url, directory = provenance_db
    _replay_export(directory / "mock_trends_2026-10-20.json")
    with psycopg.connect(url) as conn:
        seed.load_trend_exports(conn)
    database = client.get("/api/v1/meta/data-freshness").json()
    assert database["served_from"] == "db" and database["is_fallback"] is False
    with monkeypatch.context() as patch:
        patch.setattr(repository, "_get_connection", lambda **_: (_ for _ in ()).throw(OSError()))
        service.clear_cache()
        fixture = client.get("/api/v1/meta/data-freshness").json()
    assert fixture["served_from"] == "fixture" and fixture["is_fallback"] is True
    for payload in (database, fixture):
        assert payload["is_replay"] is True
        assert payload["observation_window_start"] == "2024-10-13"
        assert payload["observation_window_end"] == "2024-10-19"
        assert payload["retrieved_at"] == "2026-10-24"
        assert payload["retrieved_at_basis"] == "git_commit_date"
        assert all(
            source["retrieved_at_basis"] == "git_commit_date" for source in payload["sources"]
        )


def test_live_period_selection_excludes_replay_and_unclassified_rows(provenance_db) -> None:  # type: ignore[no-untyped-def]
    import psycopg

    from pipelines.trends import score

    url, _ = provenance_db
    with psycopg.connect(url) as conn:
        for period, replay in (("2026-W41", False), ("2026-W42", True), ("2026-W43", None)):
            conn.execute(
                "INSERT INTO skill_signal_raw (skill_id, source, metric, value, period, "
                "retrieved_at, is_replay, observation_window_start, observation_window_end, "
                "retrieved_at_basis, retrieval_evidence, total_papers) "
                "VALUES ('python', 'arxiv', 'mention_count', 1, %s, '2026-10-24', %s, "
                "'2024-10-13', '2024-10-19', 'fetch_log', 'synthetic test evidence', 1)",
                (period, replay),
            )
    assert score.list_available_periods(url) == ["2026-W41"]
    # One genuine period cannot borrow the replay as its previous week.
    assert score.load_signal_raw(url, "2026-W42")[0] == {}
    assert score.load_signal_raw(url, "2026-W43")[0] == {}


@pytest.mark.parametrize("provenance_db", ["legacy"], indirect=True)
def test_migration_repairs_identifiable_legacy_replay_rows(provenance_db) -> None:  # type: ignore[no-untyped-def]
    import psycopg
    from psycopg import sql
    from psycopg.types.json import Jsonb

    from db import migrate, seed

    url, directory = provenance_db
    export = _replay_export(directory / "mock_trends_2026-10-20.json")
    item = export["items"][0]
    with psycopg.connect(url) as conn:
        conn.execute(
            sql.SQL("INSERT INTO trend_snapshots ({}) VALUES ({})").format(
                sql.SQL(", ").join(map(sql.Identifier, seed.TREND_FIELDS)),
                sql.SQL(", ").join(sql.Placeholder() * len(seed.TREND_FIELDS)),
            ),
            tuple(item.get(key, "2026-10-20") for key in seed.TREND_FIELDS),
        )
        conn.execute(
            "INSERT INTO trend_snapshot_meta (snapshot_date, sources, provenance_note) "
            "VALUES (%s, %s, %s)",
            (
                "2026-10-20",
                Jsonb(export["meta"]["sources"]),
                export["meta"]["data_provenance_note"],
            ),
        )
        conn.execute(
            "INSERT INTO skill_signal_raw (skill_id, source, metric, value, total_papers, "
            "period, retrieved_at) "
            "VALUES ('python', 'arxiv', 'mention_count', 1, 10, '2026-W43', '2026-10-20')"
        )
        conn.execute(
            migrate.up_section(
                (migrate.MIGRATIONS / "20261030120000_trend_replay_provenance.sql").read_text(
                    encoding="utf-8"
                )
            )
        )
        for table in ("trend_snapshots", "trend_snapshot_meta", "skill_signal_raw"):
            row = conn.execute(
                sql.SQL(
                    "SELECT is_replay, observation_window_start, observation_window_end, "
                    "retrieved_at_basis FROM {}"
                ).format(sql.Identifier(table))
            ).fetchone()
            assert row == (True, date(2024, 10, 13), date(2024, 10, 19), "git_commit_date")


def test_raw_origins_do_not_mix_and_live_publish_preserves_retrieval(provenance_db) -> None:  # type: ignore[no-untyped-def]
    import psycopg

    from app.features.trends import repository
    from pipelines.trends import arxiv_ingest, run, score

    url, directory = provenance_db
    export = _replay_export(directory / "mock_trends_2026-10-20.json")
    replay = export["meta"]
    live = {
        **replay,
        "is_replay": False,
        "observation_window_start": "2026-10-19",
        "observation_window_end": "2026-10-24",
        "retrieved_at_basis": "fetch_log",
        "retrieval_evidence": "synthetic live fetch evidence",
    }
    for facts, count, total in ((replay, 50, 50), (live, 3, 100)):
        arxiv_ingest.write_signal_rows(
            {"python": count},
            total,
            date(2026, 10, 20),
            url,
            period="2026-W43",
            provenance=facts,
        )
    assert score.list_available_periods(url) == ["2026-W43"]
    assert score.load_signal_raw(url, "2026-W43") == ({"python": 3.0}, 100)
    assert score.load_signal_raw(url, "2026-W43", is_replay=True) == ({"python": 50.0}, 50)
    facts = run.live_provenance(url, "2026-W43")
    slot = date(2026, 10, 30)
    sources = [
        {
            "name": "Synthetic test source",
            "url": "https://example.test",
            "retrieved_at": "2026-10-24",
        }
    ]
    run.publish(
        export["items"][:1], slot, sources, "Synthetic publication test", url, provenance=facts
    )
    snapshot = repository.get_snapshot(slot, "moderate", strict=True)
    assert snapshot.meta.is_replay is False
    assert snapshot.meta.retrieved_at == date(2026, 10, 24)
    assert snapshot.meta.observation_window_start == date(2026, 10, 19)
    with pytest.raises(ValueError, match="cannot change origin"):
        run.publish(export["items"][:1], slot, sources, "Synthetic replay", url, provenance=replay)
    # The older scoring entrypoint must not erase the origin by bypassing publish.
    with pytest.raises(ValueError, match="cannot change origin"):
        score.write_snapshots(export["items"][:1], slot, url)
    with psycopg.connect(url) as conn:
        assert conn.execute(
            "SELECT is_replay FROM trend_snapshot_meta WHERE snapshot_date = %s", (slot,)
        ).fetchone() == (False,)


REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = REPO_ROOT / "src" / "data" / "seed"

FIXTURE_FILES = [
    SEED_DIR / "mock_trends.json",
    SEED_DIR / "mock_trends_2026-10-13.json",
    SEED_DIR / "mock_trends_2026-10-20.json",
]


@pytest.mark.parametrize("fixture_path", FIXTURE_FILES, ids=lambda p: p.name)
def test_mock_fixture_derived_fields_match_scoring_formula(fixture_path: Path) -> None:
    assert fixture_path.exists(), f"Fixture file missing: {fixture_path}"

    with fixture_path.open(encoding="utf-8") as fh:
        data = json.load(fh)

    items = data.get("items", [])
    assert items, f"Fixture {fixture_path.name} has no items"

    for item in items:
        sid = item["skill_id"]
        v_mod = float(item["velocity_moderate"])
        exp = float(item["automation_exposure"])
        v_fast = float(item["velocity_fast"])
        dir_mod = item["direction_moderate"]
        dir_fast = item["direction_fast"]

        # 1. velocity_fast consistency (1e-5 accommodates 6-decimal rounding in pipeline)
        expected_v_fast = scenario_fast(v_mod, exp)
        assert abs(v_fast - expected_v_fast) < 1e-5, (
            f"[{fixture_path.name}] {sid}: velocity_fast {v_fast} != "
            f"expected {expected_v_fast} from scenario_fast({v_mod}, {exp})"
        )

        # 2. direction_moderate consistency
        expected_dir_mod = direction(v_mod)
        assert dir_mod == expected_dir_mod, (
            f"[{fixture_path.name}] {sid}: direction_moderate '{dir_mod}' != "
            f"expected '{expected_dir_mod}' from direction({v_mod})"
        )

        # 3. direction_fast consistency
        expected_dir_fast = direction(v_fast)
        assert dir_fast == expected_dir_fast, (
            f"[{fixture_path.name}] {sid}: direction_fast '{dir_fast}' != "
            f"expected '{expected_dir_fast}' from direction({v_fast})"
        )


@pytest.mark.parametrize(
    "snap_date_str",
    ["2026-10-13", "2026-10-20"],
)
def test_mock_fixtures_faithfully_match_database_export(snap_date_str: str) -> None:
    """Assert fixture is a provably faithful export of DB rows for that snapshot date."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src" / "api"))
    from app.core.config import get_settings
    from app.core.db import database_status

    if database_status() != "ok" or not get_settings().database_url:
        pytest.skip("PostgreSQL unavailable; skipping DB export comparison.")

    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT skill_id, research_velocity, labor_decay, labor_decay_source_note,
                       automation_exposure, velocity_moderate, velocity_fast,
                       direction_moderate, direction_fast
                FROM trend_snapshots
                WHERE snapshot_date = %s
                ORDER BY skill_id
                """,
                (date.fromisoformat(snap_date_str),),
            )
            db_rows = {r["skill_id"]: r for r in cur.fetchall()}

    if not db_rows:
        pytest.skip(f"No DB rows in trend_snapshots for {snap_date_str}")

    fixture_path = SEED_DIR / f"mock_trends_{snap_date_str}.json"
    with fixture_path.open(encoding="utf-8") as fh:
        fixture_items = {i["skill_id"]: i for i in json.load(fh)["items"]}

    assert len(fixture_items) == len(db_rows), (
        f"Fixture item count ({len(fixture_items)}) != DB row count ({len(db_rows)})"
    )

    for sid, db_row in db_rows.items():
        assert sid in fixture_items, f"Missing skill {sid} in {fixture_path.name}"
        f_item = fixture_items[sid]

        assert abs(f_item["research_velocity"] - float(db_row["research_velocity"])) < 1e-5
        assert abs(f_item["labor_decay"] - float(db_row["labor_decay"])) < 1e-5
        assert f_item["labor_decay_source_note"] == db_row["labor_decay_source_note"]
        assert abs(f_item["automation_exposure"] - float(db_row["automation_exposure"])) < 1e-5
        assert abs(f_item["velocity_moderate"] - float(db_row["velocity_moderate"])) < 1e-5
        assert abs(f_item["velocity_fast"] - float(db_row["velocity_fast"])) < 1e-5
        assert f_item["direction_moderate"] == db_row["direction_moderate"]
        assert f_item["direction_fast"] == db_row["direction_fast"]
