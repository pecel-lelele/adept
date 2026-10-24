"""Fairness CI guards: protected attributes never enter the system."""

import re
from pathlib import Path
from typing import Any

import pytest

from app.core.fairness import counterfactual_diffs, is_protected, protected_terms_in
from app.main import app

MIGRATIONS = Path(__file__).resolve().parents[3] / "src" / "db" / "migrations"


PROTECTED = ["age", "user_age", "gender", "Ethnicity", "date_of_birth", "religion"]
PROTECTED += ["marital_status", "full_name", "dob"]
ORDINARY = ["page", "usage", "language", "stage", "sessions", "budget_myr", "display_name"]
ORDINARY += ["hours_per_week", "message", "average"]


@pytest.mark.parametrize("name", PROTECTED)
def test_protected_names_are_detected(name: str) -> None:
    assert is_protected(name)


@pytest.mark.parametrize("name", ORDINARY)
def test_ordinary_names_are_not_flagged(name: str) -> None:
    assert not is_protected(name)


def _schema_fields(schema: dict[str, Any], defs: dict[str, Any], seen: set[str]) -> set[str]:
    if "$ref" in schema:
        ref = schema["$ref"].rsplit("/", 1)[-1]
        if ref in seen:
            return set()
        seen.add(ref)
        return _schema_fields(defs[ref], defs, seen)
    names: set[str] = set()
    for prop, sub in schema.get("properties", {}).items():
        names.add(prop)
        names |= _schema_fields(sub, defs, seen)
    for key in ("items", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            names |= _schema_fields(schema[key], defs, seen)
    for key in ("anyOf", "allOf", "oneOf"):
        for sub in schema.get(key, []):
            names |= _schema_fields(sub, defs, seen)
    return names


def api_input_fields() -> set[str]:
    spec = app.openapi()
    defs = spec.get("components", {}).get("schemas", {})
    names: set[str] = set()
    for ops in spec["paths"].values():
        for op in ops.values():
            for param in op.get("parameters", []):
                names.add(param["name"])
            for media in op.get("requestBody", {}).get("content", {}).values():
                names |= _schema_fields(media.get("schema", {}), defs, set())
    return names


def test_no_api_input_accepts_a_protected_attribute() -> None:
    fields = api_input_fields()
    assert fields, "expected some API inputs"
    assert protected_terms_in(fields) == []


def test_no_database_column_stores_a_protected_attribute() -> None:
    columns: set[str] = set()
    for sql in MIGRATIONS.glob("*.sql"):
        up = sql.read_text(encoding="utf-8").split("-- migrate:down")[0]
        for line in up.splitlines():
            line = line.split("--", 1)[0]
            m = re.match(r"\s*(?:ADD COLUMN(?: IF NOT EXISTS)?\s+)?([a-z_]+)\s+(text|integer|"
                         r"smallint|boolean|numeric|real|date|timestamptz|bigint|jsonb|vector)",
                         line, re.I)  # fmt: skip
            if m:
                columns.add(m.group(1))
    assert {"user_id", "hours_per_week"} <= columns
    assert protected_terms_in(columns) == []


def test_counterfactual_diffs_reports_identity_sensitive_functions() -> None:
    fair = lambda p: p["skills"]  # noqa: E731
    unfair = lambda p: p["skills"] + (["bonus"] if p.get("name") == "A" else [])  # noqa: E731
    base = {"name": "A", "skills": ["sql"]}
    variants = {"renamed": {"name": "B", "skills": ["sql"]}}
    assert counterfactual_diffs(fair, base, variants) == []
    assert counterfactual_diffs(unfair, base, variants) == ["renamed"]
