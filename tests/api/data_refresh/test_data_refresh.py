"""In-app live data refresh and the public freshness endpoint.

No network and no database: outbound HTTP is httpx.MockTransport, the app database is an
in-memory store that the repository functions and the pipelines' writers are patched onto, and
the validators, classifiers and sync job are production code.
"""

from __future__ import annotations

import csv
import json
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from harness import fixtures

from app.core import accounts
from app.core.config import get_settings
from app.core.seed import SEED_DIR
from app.features.data_refresh import repository, service
from app.features.pathway import catalogue_sources as src
from pipelines.jobs import run as jobs_run
from pipelines.jobs.sources import RawPosting
from pipelines.trends import malaysia_context as dosm

ADMIN = accounts.Account("synthetic-data-admin", "Synthetic Admin", "data@example.test", "learner")
AS_ADMIN = {"X-Demo-User": ADMIN.id}
STORED_ON = date(2026, 3, 2)  # a fixed past date: never the machine's current date


class FakeStore:
    """The app database, reduced to what the refresh touches."""

    def __init__(self) -> None:
        self.courses: dict[str, date] = {}
        self.jobs: list[dict[str, Any]] = []
        self.labour: dict[str, Any] | None = None
        self.runs: list[dict[str, Any]] = []
        self.other_instance_holds_lock = False
        self.writes = 0

    def stored(self, source: str) -> repository.StoredFreshness | None:
        if source == "courses" and self.courses:
            return repository.StoredFreshness(len(self.courses), max(self.courses.values()))
        if source == "jobs" and self.jobs:
            return repository.StoredFreshness(
                len(self.jobs), max(date.fromisoformat(r["last_seen"]) for r in self.jobs)
            )
        if source == "labour" and self.labour:
            meta = self.labour["meta"]["sources"][0]
            return repository.StoredFreshness(
                1,
                date.fromisoformat(meta["retrieved_at"]),
                date.fromisoformat(self.labour["observed_month"]),
            )
        return None

    @property
    def total_rows(self) -> int:
        return len(self.courses) + len(self.jobs) + (1 if self.labour else 0)


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> FakeStore:
    db = FakeStore()

    @contextmanager
    def advisory_lock(source: str) -> Iterator[bool]:
        yield not db.other_instance_holds_lock

    def record_run(source: str, *args: Any) -> None:
        keys = (
            "started",
            "finished",
            "status",
            "fetched",
            "upserted",
            "rejected",
            "code",
            "detail",
        )
        db.runs.append({"source": source, **dict(zip(keys, args, strict=True))})

    def last_runs() -> dict[str, Any]:
        out = {}
        for r in db.runs:
            out[r["source"]] = repository.RefreshRunSummary(
                status=r["status"],
                finished_at=r["finished"],
                rows_fetched=r["fetched"],
                rows_upserted=r["upserted"],
                rows_rejected=r["rejected"],
                error_code=r["code"],
            )
        return out

    monkeypatch.setattr(service, "_storage_ready", lambda: True)
    monkeypatch.setattr(repository, "advisory_lock", advisory_lock)
    monkeypatch.setattr(repository, "record_run", record_run)
    monkeypatch.setattr(repository, "last_runs", last_runs)
    monkeypatch.setattr(repository, "stored_freshness", db.stored)
    monkeypatch.setattr(repository, "bounded_db_url", lambda: "postgresql://fake/none")

    @contextmanager
    def write_connection(deadline: float) -> Iterator[Any]:
        yield None

    monkeypatch.setattr(repository, "write_connection", write_connection)
    monkeypatch.setattr(service, "_today", lambda: STORED_ON)
    return db


@pytest.fixture(autouse=True)
def _admin_account(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    accounts.create(ADMIN, "")
    monkeypatch.setattr(get_settings(), "admin_user_ids", ADMIN.id)
    yield
    fixtures.install()


def _mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> Callable[[], httpx.Client]:
    return lambda: httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


# ---------------------------------------------------------------------------
# Authorization and guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source", ["courses", "jobs", "labour", "trends"])
def test_refresh_is_admin_only(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    called = []
    monkeypatch.setattr(service, "_RUNNERS", {source: lambda *_: called.append(1)})
    path = f"/api/v1/data/refresh/{source}"
    assert client.post(path, headers={"X-Demo-User": "v2.not-a-real-token"}).status_code == 401
    assert client.post(path, headers={"X-Demo-User": "aisyah"}).status_code == 403
    assert called == [] and store.runs == []


def test_unknown_source_is_rejected(client: TestClient, store: FakeStore) -> None:
    assert client.post("/api/v1/data/refresh/unknown", headers=AS_ADMIN).status_code == 422


def test_needs_the_database(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "_storage_ready", lambda: False)
    response = client.post("/api/v1/data/refresh/labour", headers=AS_ADMIN)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "refresh_requires_database"


def test_pipeline_missing_in_this_process_is_501(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(*_: Any) -> None:
        raise ImportError("pipelines")

    monkeypatch.setattr(service, "_RUNNERS", {"jobs": missing})
    response = client.post("/api/v1/data/refresh/jobs", headers=AS_ADMIN)
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "refresh_not_supported"
    assert store.runs[-1]["status"] == "failed"


def test_a_running_source_gives_409_in_process(client: TestClient, store: FakeStore) -> None:
    lock: threading.Lock = service._locks["labour"]
    assert lock.acquire(blocking=False)
    try:
        response = client.post("/api/v1/data/refresh/labour", headers=AS_ADMIN)
    finally:
        lock.release()
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "refresh_in_progress"
    assert store.runs == []


def test_a_run_on_another_instance_gives_409(client: TestClient, store: FakeStore) -> None:
    store.other_instance_holds_lock = True
    response = client.post("/api/v1/data/refresh/courses", headers=AS_ADMIN)
    assert response.status_code == 409
    assert service._locks["courses"].acquire(blocking=False), "the in-process lock was released"
    service._locks["courses"].release()


def test_destination_guard_refuses_non_public_hosts() -> None:
    public = lambda host: ["93.184.216.34"]  # noqa: E731
    service.assert_public_https("https://learn.microsoft.com/api", public)
    for url in (
        "http://learn.microsoft.com/api",
        "https://127.0.0.1/x",
        "https://localhost/x",
        "https://metadata.internal/x",
    ):
        with pytest.raises(httpx.UnsupportedProtocol):
            service.assert_public_https(url, public)
    with pytest.raises(httpx.UnsupportedProtocol):
        service.assert_public_https("https://rebind.example/x", lambda host: ["10.0.0.5"])


# ---------------------------------------------------------------------------
# Labour (DOSM)
# ---------------------------------------------------------------------------

LFS_CSV = "date,u_rate,p_rate,ep_ratio\n2025-12-01,3.0,70.0,68.0\n2026-01-01,3.1,70.4,68.3\n"


def _dosm(monkeypatch: pytest.MonkeyPatch, store: FakeStore, body: str, status: int = 200) -> None:
    monkeypatch.setattr(
        service, "guarded_client", _mock_client(lambda request: httpx.Response(status, text=body))
    )

    def publish(value: Any, url: str, *, conn: Any = None) -> None:
        store.writes += 1
        store.labour = value.model_dump(mode="json")

    monkeypatch.setattr(dosm, "publish", publish)


def test_labour_refresh_writes_and_moves_the_freshness_date(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dosm(monkeypatch, store, LFS_CSV)
    before = {s["source"]: s for s in client.get("/api/v1/data/freshness").json()["sources"]}
    assert before["labour"]["served_from"] == "seed" and before["labour"]["is_fallback"] is True

    response = client.post("/api/v1/data/refresh/labour", headers=AS_ADMIN)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok" and body["error_code"] is None
    assert (body["rows_fetched"], body["rows_upserted"], body["rows_rejected"]) == (1, 1, 0)
    assert store.labour is not None and store.writes == 1

    after = {s["source"]: s for s in client.get("/api/v1/data/freshness").json()["sources"]}
    assert after["labour"]["served_from"] == "database" and after["labour"]["is_fallback"] is False
    assert after["labour"]["data_as_of"] == "2026-01-01"
    assert after["labour"]["last_fetched_at"] == store.labour["meta"]["sources"][0]["retrieved_at"]
    assert after["labour"]["data_as_of"] != before["labour"]["data_as_of"]
    assert after["labour"]["last_run"]["status"] == "ok"
    assert store.runs[-1]["status"] == "ok" and store.runs[-1]["upserted"] == 1


def test_labour_upstream_error_writes_nothing_and_is_logged(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dosm(monkeypatch, store, "gateway down", status=503)
    body = client.post("/api/v1/data/refresh/labour", headers=AS_ADMIN).json()
    assert body["status"] == "failed" and body["error_code"] == "fetch_failed"
    assert store.writes == 0 and store.labour is None
    assert store.runs[-1]["status"] == "failed" and store.runs[-1]["code"] == "fetch_failed"


@pytest.mark.parametrize(
    "csv_body",
    [
        "date,u_rate,p_rate,ep_ratio\n2999-01-01,3.1,70.4,68.3\n",  # month not complete yet
        "date,u_rate,p_rate,ep_ratio\n2026-01-01,310,70.4,68.3\n",  # rate outside 0-100
        "date,u_rate\n2026-01-01,3.1\n",  # columns missing
    ],
)
def test_labour_validation_failure_writes_nothing(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch, csv_body: str
) -> None:
    _dosm(monkeypatch, store, csv_body)
    body = client.post("/api/v1/data/refresh/labour", headers=AS_ADMIN).json()
    assert body["status"] == "failed" and body["error_code"] == "validation_failed"
    assert body["rows_rejected"] == 1 and body["rows_upserted"] == 0
    assert store.writes == 0 and store.labour is None


# ---------------------------------------------------------------------------
# Courses (Microsoft Learn + Coursera + Bank Negara through the existing sync job)
# ---------------------------------------------------------------------------


class _Cursor:
    def __init__(self, rows: list[tuple[Any, ...]], rowcount: int = 0) -> None:
        self.rows, self.rowcount = rows, rowcount

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.rows[0] if self.rows else None


class _Conn:
    def __init__(self, skills: set[str]) -> None:
        self.skills, self.upserts = skills, []

    def execute(self, sql: str, params: Any = ()) -> _Cursor:
        text = " ".join(sql.split())
        if text.startswith("SELECT id FROM skills"):
            return _Cursor([(s,) for s in sorted(self.skills)])
        if text.startswith("INSERT INTO courses"):
            self.upserts.append((params[0], params[7]))  # id, verified_at
        return _Cursor([])


def _known_skills() -> set[str]:
    with (SEED_DIR / "taxonomy" / "skills.csv").open(encoding="utf-8") as fh:
        return {row["id"] for row in csv.DictReader(fh)}


def _catalog(duration: int = 60) -> dict[str, Any]:
    return {
        "modules": [
            {
                "uid": c.uid,
                "title": f"Synthetic {c.id}",
                "url": f"https://learn.microsoft.com/en-us/training/modules/{c.id}/?x=1",
                "duration_in_minutes": duration,
                "type": "module",
            }
            for c in src.CURATED
        ],
        "learningPaths": [],
    }


def _courses_world(
    monkeypatch: pytest.MonkeyPatch, store: FakeStore, catalog: dict[str, Any], skills: set[str]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host == "learn.microsoft.com":
            if request.url.path == "/api/learn/catalog":
                return httpx.Response(200, json=catalog)
            return httpx.Response(
                200,
                text="<html><title>Learning module</title>Free</html>",
                headers={"content-type": "text/html"},
            )
        if host == "api.coursera.org":
            return httpx.Response(200, json={"elements": [{}]})
        if host == "api.bnm.gov.my":
            return httpx.Response(
                200, json={"data": {"unit": 1, "rate": {"selling_rate": 4.5, "date": "2026-03-01"}}}
            )
        return httpx.Response(404)

    monkeypatch.setattr(service, "guarded_client", _mock_client(handler))

    @contextmanager
    def write_connection(deadline: float) -> Iterator[_Conn]:
        conn = _Conn(skills)
        yield conn  # committing below is skipped if production validation raises
        store.writes += 1
        store.courses.update({cid: STORED_ON for cid, _on in conn.upserts})

    monkeypatch.setattr(repository, "write_connection", write_connection)


def test_courses_refresh_upserts_and_moves_the_freshness_date(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _courses_world(monkeypatch, store, _catalog(), _known_skills())
    before = {s["source"]: s for s in client.get("/api/v1/data/freshness").json()["sources"]}
    assert before["courses"]["served_from"] == "seed"

    body = client.post("/api/v1/data/refresh/courses", headers=AS_ADMIN).json()
    assert body["status"] == "ok", body
    assert body["rows_upserted"] > 0 and body["rows_upserted"] == len(store.courses)
    assert body["rows_fetched"] >= body["rows_upserted"]

    after = {s["source"]: s for s in client.get("/api/v1/data/freshness").json()["sources"]}[
        "courses"
    ]
    assert after["served_from"] == "database" and after["is_fallback"] is False
    assert after["rows"] == len(store.courses)
    # The freshness date is the sync date kept with the rows (not the fixed verified_at dates).
    assert after["last_fetched_at"] == STORED_ON.isoformat()
    assert after["last_fetched_at"] != before["courses"]["last_fetched_at"]
    assert store.runs[-1]["source"] == "courses" and store.runs[-1]["status"] == "ok"


def test_courses_invalid_catalogue_writes_nothing(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _courses_world(monkeypatch, store, _catalog(duration=0), _known_skills())
    body = client.post("/api/v1/data/refresh/courses", headers=AS_ADMIN).json()
    assert body["status"] == "failed" and body["error_code"] == "validation_failed"
    assert body["rows_upserted"] == 0
    assert store.writes == 0 and store.courses == {}
    assert store.runs[-1]["status"] == "failed"


def test_courses_sync_validation_failure_rolls_back(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _courses_world(monkeypatch, store, _catalog(), set())  # the skills table knows nothing
    body = client.post("/api/v1/data/refresh/courses", headers=AS_ADMIN).json()
    assert body["status"] == "failed" and body["error_code"] == "validation_failed"
    assert store.writes == 0 and store.courses == {}


def test_courses_unreachable_microsoft_learn_writes_nothing(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _courses_world(monkeypatch, store, _catalog(), _known_skills())
    monkeypatch.setattr(
        service, "guarded_client", _mock_client(lambda request: httpx.Response(503, text="down"))
    )
    body = client.post("/api/v1/data/refresh/courses", headers=AS_ADMIN).json()
    assert body["status"] == "failed" and body["error_code"] == "fetch_failed"
    assert store.writes == 0 and store.courses == {}


# ---------------------------------------------------------------------------
# Jobs (existing pipeline: keyed boards only with keys, validation, one transaction)
# ---------------------------------------------------------------------------


def _posting(n: int, url: str = "https://example.test/jobs/{n}") -> RawPosting:
    return RawPosting(
        source="remotive",
        board="remotive",
        source_id=str(n),
        employer="Synthetic Employer",
        title=f"Data Analyst {n}",
        url=url.format(n=n),
        api_url="https://example.test/api",
        location="Kuala Lumpur, Malaysia",
        work_mode="remote",
        remote_scope="Worldwide",
        text="Python and SQL for reporting",
    )


def _jobs_world(
    monkeypatch: pytest.MonkeyPatch, store: FakeStore, postings: list[RawPosting]
) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def fetch(only: Any, *, selected: Any, fetcher: Any, deadline: float) -> Any:
        seen["boards"] = [b.board for b in selected]
        seen["deadline"] = deadline
        log = [{"source": "remotive", "board": "remotive", "employer": "", "status": "ok",
                "kept": len(postings)}]  # fmt: skip
        log.append(
            {"source": "himalayas", "board": "himalayas", "employer": "", "status": "error",
             "kept": 0, "detail": "boom"}
        )  # fmt: skip
        return postings, log

    def to_db(
        rows: list[dict[str, Any]], certs: Any, log: Any, today: date, url: str, conn: Any = None
    ) -> int:
        store.writes += 1
        store.jobs = [dict(r) for r in rows]
        return len(rows)

    monkeypatch.setattr(jobs_run, "fetch", fetch)
    monkeypatch.setattr(jobs_run, "cert_rows", lambda: ([], "fx"))
    monkeypatch.setattr(jobs_run, "to_db", to_db)
    return seen


def test_only_configured_keyed_boards_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAREERJET_API_KEY", "synthetic-key")
    monkeypatch.setenv("JOOBLE_API_KEY", "")
    monkeypatch.delenv("WEB3_CAREER_TOKEN", raising=False)
    chosen, skipped = service.selected_boards()
    names = [b.board for b in chosen]
    assert "careerjet-my" in names and "himalayas" not in names
    assert {b.source for b in chosen} <= {"greenhouse", "lever", "ashby", "careerjet"}
    assert "jooble-my" not in names and "web3career" not in names
    assert {"jooble-my", "web3career", "himalayas"} <= set(skipped)


def test_jobs_refresh_upserts_and_reports_boards(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CAREERJET_API_KEY", "")
    seen = _jobs_world(monkeypatch, store, [_posting(1), _posting(2)])
    body = client.post("/api/v1/data/refresh/jobs", headers=AS_ADMIN).json()
    assert body["status"] == "ok", body
    assert (body["rows_fetched"], body["rows_upserted"], body["rows_rejected"]) == (2, 2, 0)
    assert body["boards_run"] == ["remotive"]
    assert "himalayas" in body["boards_skipped"] and "careerjet-my" in body["boards_skipped"]
    assert "careerjet-my" not in seen["boards"]
    assert len(store.jobs) == 2
    assert all(r["last_seen"] == STORED_ON.isoformat() for r in store.jobs)

    fresh = {s["source"]: s for s in client.get("/api/v1/data/freshness").json()["sources"]}["jobs"]
    assert fresh["served_from"] == "database" and fresh["rows"] == 2
    assert fresh["last_fetched_at"] == STORED_ON.isoformat()


def test_jobs_invalid_rows_write_nothing(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = [_posting(n, url="http://example.test/{n}") for n in range(3)]
    _jobs_world(monkeypatch, store, bad)
    body = client.post("/api/v1/data/refresh/jobs", headers=AS_ADMIN).json()
    assert body["status"] == "failed" and body["error_code"] == "validation_failed"
    assert body["rows_rejected"] == 3 and body["rows_upserted"] == 0
    assert store.writes == 0 and store.jobs == []


def test_jobs_with_no_openings_writes_nothing(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _jobs_world(monkeypatch, store, [])
    body = client.post("/api/v1/data/refresh/jobs", headers=AS_ADMIN).json()
    assert body["status"] == "failed" and body["error_code"] == "fetch_failed"
    assert store.writes == 0


def test_incomplete_course_checks_rotate_without_publishing_or_recording_success(
    client: TestClient, store: FakeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.features.data_refresh import course_checks

    payload = _catalog()
    _courses_world(monkeypatch, store, payload, _known_skills())
    expected = src.all_rows(payload, STORED_ON, allow_missing=True)
    visited = []
    monkeypatch.setattr(service.secrets, "randbelow", lambda size: size - 1)

    def incomplete(rows: list[Any], *args: Any) -> list[Any]:
        visited.append(rows[0].id)
        raise TimeoutError("Synthetic exhausted verification budget")

    monkeypatch.setattr(course_checks, "checked_rows", incomplete)
    body = client.post("/api/v1/data/refresh/courses", headers=AS_ADMIN).json()
    assert body["status"] == "failed" and body["error_code"] == "incomplete_checks"
    assert visited == [expected[-1].id] and visited != [expected[0].id]
    assert store.writes == 0 and store.runs[-1]["status"] == "failed"


# ---------------------------------------------------------------------------
# Freshness
# ---------------------------------------------------------------------------


def test_freshness_is_public_and_lists_every_source(client: TestClient, store: FakeStore) -> None:
    response = client.get("/api/v1/data/freshness")  # no admin header
    assert response.status_code == 200
    items = {s["source"]: s for s in response.json()["sources"]}
    assert set(items) == {"trends", "courses", "jobs", "labour"}
    assert items["trends"]["refreshable"] is True
    assert all(items[s]["refreshable"] for s in ("courses", "jobs", "labour"))
    for item in items.values():
        assert item["source_name"]


def test_freshness_dates_come_from_stored_data_not_the_clock(
    client: TestClient, store: FakeStore
) -> None:
    store.courses = {"c1": STORED_ON}
    store.jobs = [{"last_seen": STORED_ON.isoformat()}]
    items = {s["source"]: s for s in client.get("/api/v1/data/freshness").json()["sources"]}
    assert items["courses"]["last_fetched_at"] == STORED_ON.isoformat()
    assert items["jobs"]["last_fetched_at"] == STORED_ON.isoformat()
    assert items["courses"]["served_from"] == "database"
    assert items["courses"]["rows"] == 1


def test_freshness_falls_back_to_the_dated_seed(client: TestClient, store: FakeStore) -> None:
    items = {s["source"]: s for s in client.get("/api/v1/data/freshness").json()["sources"]}
    verified = [
        date.fromisoformat(r["verified_at"][:10])
        for r in csv.DictReader((SEED_DIR / "courses" / "courses.csv").open(encoding="utf-8"))
    ]
    assert items["courses"]["last_fetched_at"] == min(verified).isoformat()
    assert items["courses"]["served_from"] == "seed" and items["courses"]["is_fallback"] is True
    log = json.loads((Path(SEED_DIR) / "jobs" / "fetch_log.json").read_text(encoding="utf-8"))
    assert items["jobs"]["last_fetched_at"] == log["fetched_on"]
    labour = json.loads((SEED_DIR / "trends" / "malaysia_labour.json").read_text(encoding="utf-8"))
    assert items["labour"]["last_fetched_at"] == labour["meta"]["sources"][0]["retrieved_at"]
    assert items["labour"]["data_as_of"] == labour["observed_month"]
