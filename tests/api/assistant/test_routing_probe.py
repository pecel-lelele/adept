"""Routing regression: each realistic question reaches the answer block it asks for.

Cases live in fixtures/routing_cases.tsv (question, audience, accepted intents joined by "|").
"""

from pathlib import Path

import pytest

from app.features.assistant import guide

CASES_FILE = Path(__file__).parent / "fixtures" / "routing_cases.tsv"


def _load() -> list[tuple[str, str, frozenset[str]]]:
    rows: list[tuple[str, str, frozenset[str]]] = []
    for line in CASES_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        question, audience, accepted = line.split("\t")
        rows.append((question, audience, frozenset(accepted.split("|"))))
    return rows


CASES = _load()


def test_fixture_has_enough_cases() -> None:
    assert len(CASES) >= 80


@pytest.mark.parametrize(("question", "audience", "accepted"), CASES)
def test_routes_to_accepted_intent(question: str, audience: str, accepted: frozenset[str]) -> None:
    got = guide.intents(question, audience)
    assert got[0] in accepted, f"{question!r} -> {got}, accepted {sorted(accepted)}"


def test_action_not_supported_names_every_unsupported_action() -> None:
    for locale in ("en", "ms", "zh"):
        text = guide.T[locale]["action_not_supported"]
        assert "[[page:/app/pathway]]" in text
        assert "[[page:/app/jobs]]" in text
