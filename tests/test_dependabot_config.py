"""Local Dependabot configuration validation; no remote updates are triggered."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_dependabot_yaml_covers_locked_workspace_ecosystems() -> None:
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text(encoding="utf-8"))
    assert config["version"] == 2
    updates = {(item["package-ecosystem"], item["directory"]): item for item in config["updates"]}
    assert ("uv", "/") in updates
    assert ("npm", "/") in updates
    assert ("github-actions", "/") in updates
    assert ("pip", "/src/pipelines/trends/runpod") in updates
    assert all(item["schedule"]["interval"] == "weekly" for item in config["updates"])


def test_dependabot_sends_one_grouped_pull_request_per_ecosystem() -> None:
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text(encoding="utf-8"))
    for item in config["updates"]:
        assert item["open-pull-requests-limit"] == 1
        groups = item["groups"]
        assert len(groups) == 1
        assert next(iter(groups.values()))["patterns"] == ["*"]
