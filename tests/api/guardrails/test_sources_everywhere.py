"""Handbook rule: every recommendation, score or trend carries its source and date.

Sweeps every GET endpoint whose response schema has a `meta` field (RecommendationMeta) and
checks the live response, so a new endpoint without sources fails CI automatically.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.contracts.common import RecommendationMeta
from app.main import app

PATH_VALUES = {"role_id": "data-analyst", "skill_id": "python", "state": "Kuala Lumpur"}
QUERY_VALUES = {"role_id": "data-analyst"}


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


@pytest.mark.parametrize(("path", "query"), ENDPOINTS, ids=[p for p, _ in ENDPOINTS])
@pytest.mark.parametrize("persona", ["aisyah", "demo-company"])
def test_every_recommendation_cites_dated_sources(
    client: TestClient, path: str, query: dict[str, str], persona: str
) -> None:
    resp = client.get(path, params=query, headers={"X-Demo-User": persona})
    assert resp.status_code == 200, f"{path}: {resp.text}"
    metas = _metas(resp.json())
    assert metas, f"{path} has no meta"
    for raw in metas:
        meta = RecommendationMeta.model_validate(raw)
        assert meta.sources and meta.snapshot_date
        for src in meta.sources:
            assert src.name and src.retrieved_at
            assert src.url or src.name == "MOCK DATA", f"{path}: {src.name} has no URL"
