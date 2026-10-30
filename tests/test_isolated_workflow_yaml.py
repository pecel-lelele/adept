"""Syntax-only validation; this does not execute a GitHub workflow."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["trends-refresh.yml", "data-sources.yml"])
def test_refresh_workflow_yaml_parses(name: str) -> None:
    document = yaml.safe_load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    assert isinstance(document["jobs"], dict)
