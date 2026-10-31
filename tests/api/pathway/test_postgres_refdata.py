"""Reference data (catalogue, SDGs) is read from PostgreSQL when M3_BACKEND=postgres."""

import json

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.contracts.pathway import CatalogueResponse
from app.contracts.sdg import SdgGoalListResponse
from app.core import refdata
from app.core.config import get_settings
from app.features.pathway import data
from src.db import migrate

pytestmark = pytest.mark.usefixtures("pg_backend")


def test_goals_and_catalogue_come_from_the_database(client: TestClient) -> None:
    refdata.invalidate()
    goals = SdgGoalListResponse.model_validate(client.get("/api/v1/sdg/goals").json())
    assert sum(len(g.targets) for g in goals.goals) == 169
    catalogue = CatalogueResponse.model_validate(client.get("/api/v1/pathway/catalogue").json())
    assert catalogue.courses and all(c.source for c in catalogue.courses)


def test_retired_courses_are_never_recommended() -> None:
    url = get_settings().database_url
    course_id = "mslearn-pad-start"
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("UPDATE courses SET retired_at = now() WHERE id = %s", (course_id,))
    try:
        refdata.invalidate()
        assert course_id not in {c.id for c in data.catalogue()}
    finally:
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("UPDATE courses SET retired_at = NULL WHERE id = %s", (course_id,))
        refdata.invalidate()


def test_reads_fall_back_to_seed_files_when_the_database_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            get_settings(),
            "database_url",
            "postgresql://nobody:x@127.0.0.1:1/none?connect_timeout=1",
        )
        refdata.invalidate()
        assert data.catalogue(), "seed fallback keeps the catalogue available"
    refdata.invalidate()


def test_digital_focus_migration_removes_only_the_retired_edges_and_rolls_back() -> None:
    """Use a connection-local fixture table, never alter actual role requirements."""
    from app.core import seed

    manifest = json.loads((seed.SEED_DIR / "taxonomy/provenance.json").read_text(encoding="utf-8"))
    removed = manifest["skill_bank_focus"]["removed_target_requirements"]
    current = seed.rows("taxonomy", "role_skills")
    sql = (migrate.MIGRATIONS / "20261031130000_pathway_digital_skill_focus.sql").read_text(
        encoding="utf-8"
    )
    with psycopg.connect(get_settings().database_url) as conn:
        conn.execute("CREATE TEMP TABLE role_skills (LIKE public.role_skills INCLUDING ALL)")
        for row in [*current, *removed]:
            conn.execute(
                "INSERT INTO role_skills (role_id, skill_id, required_level, importance) "
                "VALUES (%s, %s, %s, %s)",
                (row["role_id"], row["skill_id"], row["required_level"], row["importance"]),
            )

        def stored() -> set[tuple[str, str, int, float]]:
            return {
                (r[0], r[1], r[2], round(float(r[3]), 4))
                for r in conn.execute(
                    "SELECT role_id, skill_id, required_level, importance FROM role_skills"
                ).fetchall()
            }

        before = stored()
        conn.execute(migrate.up_section(sql))
        expected = {
            (
                r["role_id"],
                r["skill_id"],
                int(r["required_level"]),
                round(float(r["importance"]), 4),
            )
            for r in current
        }
        assert stored() == expected
        conn.execute(sql.split("-- migrate:down", 1)[1])
        assert stored() == before
        conn.execute(migrate.up_section(sql))
        assert stored() == expected
