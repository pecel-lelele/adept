"""Counterfactual fairness harness: production parser + matching on the synthetic demo CVs."""

import ast
import json
from pathlib import Path

import pytest

from pipelines.guardrails import matching_counterfactual as harness

DEMO_CVS = sorted(harness.DEMO_CVS.glob("*.pdf"))


def test_scoring_inputs_have_no_protected_attributes() -> None:
    harness.check_scoring_inputs()
    fields = harness.scoring_input_fields()
    assert fields["MatchProfile"] == ["skills", "interests"]
    for forbidden in ("age", "gender", "background"):
        assert forbidden not in fields["Profile"]


def test_the_harness_patches_nothing() -> None:
    tree = ast.parse(Path(harness.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    } | {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not {name for name in imported if name and "mock" in name}


def test_variants_change_identity_only() -> None:
    text = "SYNTHETIC PERSON\nAnalyst\nsynthetic.person@example.test\nSKILLS\nSQL; Python."
    variants = harness.cv_variants(text, "OTHER PERSON")
    assert variants["baseline"] == text
    swapped = variants["name-swap:Other Person"]
    assert "SYNTHETIC PERSON" not in swapped and "other.person@example.test" in swapped
    for label in ("pronouns-she", "gender-male", "age-58", "title-ms"):
        assert variants[label] != text and variants[label].endswith("SQL; Python.")


@pytest.mark.skipif(len(DEMO_CVS) < 2, reason="synthetic demo CVs are not present")
def test_demo_cvs_keep_skills_and_ranks_under_identity_swaps() -> None:
    report = harness.check_matching_counterfactual(DEMO_CVS)
    assert report["invariant"]
    files = {case["file"] for case in report["cases"]}
    assert files == {path.name for path in DEMO_CVS}
    variants = {case["variant"] for case in report["cases"]}
    assert {"baseline", "pronouns-she", "pronouns-he", "gender-female", "age-58"} <= variants
    assert any(v.startswith("name-swap:") for v in variants)
    assert all(case["skills"] > 0 and case["top_role"] for case in report["cases"])


def test_a_result_that_depends_on_the_name_is_reported() -> None:
    # A synthetic "name" that is also catalogue skill wording proves the check can fail.
    texts = {
        "a.txt": "SYNTHETIC PERSON\nAnalyst\nSKILLS\nSQL; Excel; data visualisation.",
        "b.txt": "PYTHON PROGRAMMING\nAnalyst\nSKILLS\nSQL; Excel; data visualisation.",
    }
    with pytest.raises(AssertionError, match="a.txt:name-swap"):
        harness.check_matching_counterfactual(
            [Path(name) for name in texts], read=lambda path: texts[path.name]
        )


def test_cli_writes_a_log_without_cv_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    texts = {
        "a.txt": "SYNTHETIC PERSON\nAnalyst\nSKILLS\nSQL; Excel; data visualisation.",
        "b.txt": "OTHER PERSON\nAnalyst\nSKILLS\nPython; SQL.",
    }

    original = harness.run_cv_counterfactuals

    def fixtures(paths=None, scenario="moderate", read=harness.read_pdf):  # type: ignore[no-untyped-def]
        return original([Path(name) for name in texts], scenario, lambda path: texts[path.name])

    monkeypatch.setattr(harness, "run_cv_counterfactuals", fixtures)
    out = tmp_path / "fairness.json"
    assert harness.main(["--out", str(out)]) == 0
    log = json.loads(out.read_text(encoding="utf-8"))
    assert log["invariant"] and log["snapshot_date"] and log["cases"]
    dumped = out.read_text(encoding="utf-8")
    assert "SKILLS" not in dumped and "data visualisation" not in dumped
