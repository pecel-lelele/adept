"""Tests for interest sanitising (Prompt 6, Part A).

Verifies:
  - "agentic AI" is kept.
  - "age", "Age" and "gender" are dropped.
  - "management", "language", "package", "age-friendly design" are kept.
  - Only exact matches against {"age", "gender", "race", "ethnicity", "religion",
    "nationality", "disability"} after normalisation (lowercase, strip punctuation,
    collapse whitespace) are dropped.
  - Substring/prefix matches like "agentic AI" or "management" are NOT dropped.
"""

from __future__ import annotations

from app.features.profile.service import _sanitise_interests


def test_agentic_ai_is_kept() -> None:
    """'agentic AI' must not be dropped just because it starts with 'age'."""
    assert _sanitise_interests(["agentic AI"]) == ["agentic AI"]


def test_blocked_demographic_terms_are_dropped() -> None:
    """'age', 'Age', and 'gender' must be dropped."""
    raw = ["age", "Age", "gender", "race", "ethnicity", "religion", "nationality", "disability"]
    assert _sanitise_interests(raw) == []


def test_words_containing_blocked_substrings_are_kept() -> None:
    """'management', 'language', 'package', 'age-friendly design' must be kept."""
    raw = ["management", "language", "package", "age-friendly design"]
    assert _sanitise_interests(raw) == raw


def test_whitespace_and_punctuation_normalisation() -> None:
    """Tokens with trailing/leading spaces or punctuation matching blocked terms are dropped."""
    raw = ["  age  ", "gender!", " religion... ", "AI", "cloud computing"]
    assert _sanitise_interests(raw) == ["AI", "cloud computing"]


def test_mixed_list_sanitising() -> None:
    raw = [
        "Python",
        "Age",
        "agentic AI",
        "gender",
        "management",
        "race",
        "data science",
        "age-friendly design",
    ]
    expected = [
        "Python",
        "agentic AI",
        "management",
        "data science",
        "age-friendly design",
    ]
    assert _sanitise_interests(raw) == expected
