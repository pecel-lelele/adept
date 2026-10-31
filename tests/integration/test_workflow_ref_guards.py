"""Secret-bearing dispatch jobs must not run branch code with deployment credentials."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
TRUSTED_REF = "github.ref == 'refs/heads/main' && github.repository == 'pecel-lelele/adept'"


@pytest.mark.parametrize(
    ("workflow_name", "jobs"),
    [
        ("automatic-data-refresh.yml", ("refresh",)),
        ("data-sources.yml", ("catalogue-refresh", "refresh-dry-run", "jobs-refresh")),
        ("trends-refresh.yml", ("refresh",)),
    ],
)
def test_dispatch_jobs_are_pinned_to_main_in_source_repository(
    workflow_name: str, jobs: tuple[str, ...]
) -> None:
    workflow = yaml.safe_load((WORKFLOWS / workflow_name).read_text(encoding="utf-8"))
    trigger = workflow.get("on", workflow.get(True))
    assert "workflow_dispatch" in trigger
    assert set(workflow["jobs"]) == set(jobs)
    for name, job in workflow["jobs"].items():
        expected = TRUSTED_REF
        if name == "catalogue-refresh":
            expected = "github.event_name == 'workflow_dispatch' && " + expected
        assert job.get("if") == expected
        for step in job["steps"]:
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step.get("with", {}).get("persist-credentials") is False


def test_ci_lints_each_dispatch_workflow() -> None:
    ci = yaml.safe_load((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))
    steps = ci["jobs"]["minilm-workflow"]["steps"]
    lint = next(step["run"] for step in steps if step.get("name") == "Lint workflow syntax")
    for name in ("automatic-data-refresh.yml", "data-sources.yml", "trends-refresh.yml"):
        assert f".github/workflows/{name}" in lint
