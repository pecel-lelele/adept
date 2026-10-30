"""Handbook rule: every recommendation, score or trend carries its source and date.

Sweeps every GET endpoint whose response schema has a `meta` field (RecommendationMeta) and
checks the live response, so a new endpoint without sources fails CI automatically.
POST/PUT/PATCH routes with a `meta` response are swept too, each with a synthetic fixture
request; a new one without a fixture fails `test_every_write_route_with_meta_has_a_fixture`.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from harness import fixtures
from harness.workspaces import accept_work_plan, work_headers

from app.contracts.common import RecommendationMeta
from app.features.org import funding_store
from app.features.pathway import repository as pathway_repository
from app.features.pathway import verification
from app.features.trends import repository as trends_repository
from app.main import app

PATH_VALUES = {"role_id": "data-analyst", "skill_id": "python", "state": "Kuala Lumpur"}
QUERY_VALUES = {
    "role_id": "data-analyst",
    # Trend replay compares against an earlier snapshot: use the oldest stored one.
    "from_date": trends_repository.list_available_dates()[0].isoformat(),
}


def _schema_has_meta(schema: dict[str, Any], defs: dict[str, Any]) -> bool:
    if "$ref" in schema:
        schema = defs[schema["$ref"].rsplit("/", 1)[-1]]
    return "meta" in schema.get("properties", {})


def _recommendation_gets() -> list[tuple[str, dict[str, str]]]:
    spec = app.openapi()
    defs = spec["components"]["schemas"]
    out: list[tuple[str, dict[str, str]]] = []
    for path, ops in spec["paths"].items():
        op = ops.get("get")
        if not op:
            continue
        schema = op["responses"]["200"]["content"]["application/json"]["schema"]
        if not _schema_has_meta(schema, defs):
            continue
        url = path
        for name, value in PATH_VALUES.items():
            url = url.replace("{" + name + "}", value)
        query = {
            p["name"]: QUERY_VALUES[p["name"]]
            for p in op.get("parameters", [])
            # Required parameters, plus a role for endpoints that otherwise fall back to the
            # learner's saved plan (the fixtures have none).
            if p["in"] == "query" and (p.get("required") or p["name"] in QUERY_VALUES)
        }
        out.append((url, query))
    return out


ENDPOINTS = _recommendation_gets()


def test_sweep_found_the_recommendation_endpoints() -> None:
    paths = {p for p, _ in ENDPOINTS}
    for expected in (
        "/api/v1/matches",
        "/api/v1/pathway",
        "/api/v1/trends/radar",
        "/api/v1/sdg/contribution/me",
        "/api/v1/org/plan",
    ):
        assert any(p.startswith(expected) for p in paths), expected


def _metas(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if isinstance(node.get("meta"), dict):
            found.append(node["meta"])
        for value in node.values():
            found += _metas(value)
    elif isinstance(node, list):
        for item in node:
            found += _metas(item)
    return found


# Team data is for managers only; a learner gets 403 there (tests/api/org/test_member_privacy.py).
MANAGER_ONLY = ("/api/v1/org/", "/api/v1/sdg/contribution/org", "/api/v1/sdg/contribution/region")


@pytest.mark.parametrize(("path", "query"), ENDPOINTS, ids=[p for p, _ in ENDPOINTS])
@pytest.mark.parametrize("persona", ["aisyah", "demo-company"])
def test_every_recommendation_cites_dated_sources(
    client: TestClient, path: str, query: dict[str, str], persona: str
) -> None:
    headers = {"X-Demo-User": persona}
    if persona == "demo-company" and not path.startswith(MANAGER_ONLY):
        headers["X-Workspace"] = "personal"  # a manager's own learning is personal
    resp = client.get(path, params=query, headers=headers)
    if persona == "aisyah" and path.startswith(MANAGER_ONLY):
        assert resp.status_code == 403, f"{path} leaks team data to a member"
        return
    assert resp.status_code == 200, f"{path}: {resp.text}"
    metas = _metas(resp.json())
    assert metas, f"{path} has no meta"
    for raw in metas:
        meta = RecommendationMeta.model_validate(raw)
        assert meta.sources and meta.snapshot_date
        for src in meta.sources:
            assert src.name and src.retrieved_at
            assert src.url or src.name == "MOCK DATA", f"{path}: {src.name} has no URL"


# --- write routes (POST/PUT/PATCH) that return `meta` -----------------------------------

HR = {"X-Demo-User": "demo-company"}
LEARNER = {"X-Demo-User": "aisyah"}
PLAN_ROLE = "process-automation-analyst"
CV_TEXT = b"Synthetic CV\nSKILLS\nPython; SQL; Excel; data visualisation."


def _recommendation_writes() -> set[tuple[str, str]]:
    spec = app.openapi()
    defs = spec["components"]["schemas"]
    out: set[tuple[str, str]] = set()
    for path, ops in spec["paths"].items():
        for method in ("post", "put", "patch"):
            op = ops.get(method)
            if not op:
                continue
            for code, response in op["responses"].items():
                schema = response.get("content", {}).get("application/json", {}).get("schema")
                if code.startswith("2") and schema and _schema_has_meta(schema, defs):
                    out.add((method.upper(), path))
    return out


def _saved_plan_courses(client: TestClient) -> list[str]:
    plan = client.post("/api/v1/pathway/plans", json={"role_id": PLAN_ROLE}, headers=LEARNER)
    assert plan.status_code == 200, plan.text
    return [c["id"] for s in plan.json()["pathway"]["steps"] for c in s["courses"]]


def _assistant(client: TestClient) -> Any:
    body = {"messages": [{"role": "user", "content": "Which roles suit me?"}]}
    return client.post("/api/v1/assistant/chat", json=body, headers=LEARNER)


def _packages_select(client: TestClient) -> Any:
    params = {"role_id": "data-analyst", "member_ids": ["aisyah"]}
    offers = client.get("/api/v1/org/packages", headers=HR, params=params)
    assert offers.status_code == 200, offers.text
    offer = offers.json()["packages"][0]
    body = {
        "kind": offer["kind"],
        "token": offer["token"],
        "role_id": offer["role_id"],
        "member_ids": ["aisyah"],
        "scenario": "moderate",
    }
    return client.post("/api/v1/org/packages/select", headers=HR, json=body)


def _programmes_generate(client: TestClient) -> Any:
    options = client.get("/api/v1/org/programmes/options", headers=HR)
    assert options.status_code == 200, options.text
    brief = {
        "title": "Synthetic reporting programme",
        "objectives": ["ai_adoption", "data_driven"],
        "roles": [{"role_id": "data-analyst", "headcount": 1}],
        "member_ids": [m["user_id"] for m in options.json()["members"]],
        "target_date": (datetime.now(UTC).date() + timedelta(weeks=12)).isoformat(),
        "hours_per_week": 4,
        "budget_total_myr": 3000,
        "budget_per_member_myr": 2000,
    }
    return client.post("/api/v1/org/programmes/generate", headers=HR, json=brief)


def _progress(client: TestClient) -> Any:
    course = _saved_plan_courses(client)[0]
    body = {"role_id": PLAN_ROLE, "course_id": course, "status": "completed"}
    return client.post("/api/v1/pathway/progress", json=body, headers=LEARNER)


def _progress_evidence(client: TestClient) -> Any:
    course = _saved_plan_courses(client)[0]
    url = "https://www.credly.com/badges/synthetic-badge"
    body = {"role_id": PLAN_ROLE, "course_id": course, "url": url}
    return client.post("/api/v1/pathway/progress/evidence", json=body, headers=LEARNER)


def _progress_share(client: TestClient) -> Any:
    course = _saved_plan_courses(client)[0]
    done = {"role_id": PLAN_ROLE, "course_id": course, "status": "completed"}
    assert client.post("/api/v1/pathway/progress", json=done, headers=LEARNER).status_code == 200
    accept_work_plan(PLAN_ROLE)
    body = {"role_id": PLAN_ROLE, "course_id": course}
    return client.post("/api/v1/pathway/progress/share", json=body, headers=work_headers())


def _preview_cv(client: TestClient) -> Any:
    return client.post(
        "/api/v1/preview/cv",
        params={"include_suggestions": "false"},
        data={"synthetic_consent": "true"},
        files={"file": ("synthetic.txt", CV_TEXT, "text/plain")},
    )


def _profile_cv(client: TestClient) -> Any:
    return client.post(
        "/api/v1/profile/cv",
        params={"include_suggestions": "false"},
        files={"file": ("synthetic.txt", CV_TEXT, "text/plain")},
        headers=LEARNER,
    )


def _skills_resolve(client: TestClient) -> Any:
    return client.post("/api/v1/profile/skills/resolve", json={"query": "Pyhton"}, headers=LEARNER)


WRITE_FIXTURES: dict[tuple[str, str], Callable[[TestClient], Any]] = {
    ("POST", "/api/v1/assistant/chat"): _assistant,
    ("POST", "/api/v1/org/packages/select"): _packages_select,
    ("POST", "/api/v1/org/programmes/generate"): _programmes_generate,
    ("POST", "/api/v1/pathway/progress"): _progress,
    ("POST", "/api/v1/pathway/progress/evidence"): _progress_evidence,
    ("POST", "/api/v1/pathway/progress/share"): _progress_share,
    ("POST", "/api/v1/preview/cv"): _preview_cv,
    ("POST", "/api/v1/profile/cv"): _profile_cv,
    ("POST", "/api/v1/profile/skills/resolve"): _skills_resolve,
}


def test_every_write_route_with_meta_has_a_fixture() -> None:
    assert _recommendation_writes() == set(WRITE_FIXTURES)


@pytest.fixture
def _fresh_write_state(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures.install()
    funding_store._memory.clear()
    pathway_repository.reset()
    # Never reach an external certificate page from the sweep.
    monkeypatch.setattr(verification, "probe", lambda url: 200)


@pytest.mark.usefixtures("_fresh_write_state")
@pytest.mark.parametrize("route", sorted(WRITE_FIXTURES), ids=lambda r: f"{r[0]} {r[1]}")
def test_every_write_recommendation_cites_dated_sources(
    client: TestClient, route: tuple[str, str]
) -> None:
    resp = WRITE_FIXTURES[route](client)
    assert resp.status_code == 200, f"{route}: {resp.text}"
    metas = _metas(resp.json())
    assert metas, f"{route} has no meta"
    for raw in metas:
        meta = RecommendationMeta.model_validate(raw)
        assert meta.sources and meta.snapshot_date, route
        for src in meta.sources:
            assert src.name and src.retrieved_at
            assert src.url or src.name == "MOCK DATA", f"{route}: {src.name} has no URL"
