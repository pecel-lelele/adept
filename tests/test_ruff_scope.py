"""Keep repository-wide Ruff checks focused on maintained application sources."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ruff_excludes_bundled_guides_without_weakening_application_checks() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["ruff"]

    assert set(config["extend-exclude"]) == {
        "src/web",
        "src/data",
        ".local/skills",
        ".local/secondary_skills",
    }
    assert config["lint"]["select"] == ["E", "F", "I", "B", "UP", "W"]
