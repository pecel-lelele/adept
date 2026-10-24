"""Reference data (catalogue, SDGs) is read from PostgreSQL when M3_BACKEND=postgres."""

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.contracts.pathway import CatalogueResponse
from app.contracts.sdg import SdgGoalListResponse
from app.core import refdata
from app.core.config import get_settings
from app.features.pathway import data

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
