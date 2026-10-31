"""Operator backfill: pure equivalence metrics, target safety and resume gate (M1-024, M1-027)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from pipelines.trends import backfill


def test_spearman_handles_ties_and_flat_inputs() -> None:
    assert backfill.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert backfill.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert backfill.average_ranks([5, 1, 5]) == [2.5, 1.0, 2.5]
    assert backfill.spearman([1, 1, 1], [1, 2, 3]) == 0.0


def test_the_written_pass_bar_needs_every_part() -> None:
    assert backfill.verdict(0.6, 0.7, 0.7, 500, 50, 50)
    assert not backfill.verdict(0.59, 0.9, 0.9, 900, 50, 50)
    assert not backfill.verdict(0.9, 0.69, 0.9, 900, 50, 50)
    assert not backfill.verdict(0.9, 0.9, 0.69, 900, 50, 50)
    assert not backfill.verdict(0.9, 0.9, 0.9, 499, 50, 50)
    assert not backfill.verdict(0.9, 0.9, 0.9, 900, 49, 50)
    assert not backfill.verdict(0.9, 0.9, 0.9, 900, 50, 49)


def test_comparison_cannot_pass_when_recent_windows_have_no_shared_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    day = date(2026, 10, 5)
    papers = [{"arxiv_id": f"synthetic-{i}"} for i in range(500)]
    skills = {p["arxiv_id"]: ["python"] for p in papers}
    sample = backfill.Sample({day: papers}, skills, {day: papers})
    monkeypatch.setattr(backfill, "_skills", lambda: [("python", "Python"), ("sql", "SQL")])
    report = backfill.compare(
        sample, skills, 0.5, 1.0, date(2026, 10, 1), date(2026, 10, 28), date(2026, 10, 31)
    )
    assert report["papers"] == 500 and report["spearman"] == 1.0
    assert report["recent_window_papers"] == {"before": 0, "after": 0}
    assert report["label_agreement_moderate"] == report["label_agreement_fast"] == 1.0
    assert report["passed"] is False


def test_labels_come_from_the_production_scorer() -> None:
    ids = ["a", "b"]
    out = backfill.labels({"a": 1, "b": 9}, 100, {"a": 9, "b": 1}, 100, ids, {}, {"a": 0.5})
    assert out["a"][0] == "rising" and out["b"][0] == "declining"
    assert backfill.label_agreement(out, out, 0) == 1.0
    assert backfill.label_agreement(out, {**out, "b": ("rising", "rising")}, 1) == 0.5


def test_estimate_matches_the_sampling_limits() -> None:
    plan = backfill.estimate(304)
    assert plan["papers"] == 15_200
    assert plan["arxiv_minutes"] == pytest.approx(17.7)
    assert plan["gemini_batches"] == 153
    assert plan["gemini_usd_estimate"] == pytest.approx(0.8, abs=0.01)


def test_writes_need_the_resolved_target_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backfill, "resolved_target", lambda: "db.example.test:5432/adept")
    backfill.require_target("db.example.test:5432/adept")
    with pytest.raises(SystemExit, match="Refusing to write"):
        backfill.require_target(None)
    with pytest.raises(SystemExit, match="Refusing to write"):
        backfill.require_target("other:5432/adept")


def test_backfill_will_not_start_without_a_passing_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TRENDS_MATCHER", "gemini")
    monkeypatch.setattr(backfill.trend_fallback, "enabled", lambda: True)
    monkeypatch.setattr(backfill, "REPORT", tmp_path / "missing.json")
    monkeypatch.setattr(
        backfill.automatic_trends, "catch_up", lambda *a, **k: pytest.fail("paid run started")
    )
    with pytest.raises(SystemExit, match="No passing equivalence"):
        backfill.run_backfill()
    report = tmp_path / "report.json"
    report.write_text('{"passed": false, "model": "m"}', encoding="utf-8")
    monkeypatch.setattr(backfill, "REPORT", report)
    assert not backfill.passing_report("m")
    report.write_text('{"passed": true, "model": "other"}', encoding="utf-8")
    assert not backfill.passing_report("m")
    report.write_text('{"passed": true, "model": "m"}', encoding="utf-8")
    assert backfill.passing_report("m")


def test_backfill_resumes_after_a_failed_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDS_MATCHER", "gemini")
    monkeypatch.setattr(backfill.trend_fallback, "enabled", lambda: True)
    monkeypatch.setattr(backfill, "passing_report", lambda _model: True)
    monkeypatch.setattr(backfill, "RETRY_WAIT_S", 0)
    day = date(2026, 1, 1)
    stored: dict[date, date] = {}
    monkeypatch.setattr(backfill.trend_store, "fetched_days", lambda: dict(stored))
    remaining = [
        [day, day + timedelta(days=1)],
        [day + timedelta(days=1)],
        [day + timedelta(days=1)],
        [],
    ]
    monkeypatch.setattr(backfill.automatic_trends, "missing_days", lambda _s, _t: remaining.pop(0))
    calls: list[list[date]] = []

    def catch_up(missing: list[date], *a: object, **k: object) -> tuple[int, int]:
        calls.append(list(missing))
        if len(calls) == 2:
            raise OSError("Synthetic outage")
        return 1, 50

    monkeypatch.setattr(backfill.automatic_trends, "catch_up", catch_up)
    published: list[object] = []

    def publish(*args: object) -> object:
        published.append(args)
        return type("Outcome", (), {"message": "synthetic"})()

    monkeypatch.setattr(backfill.automatic_trends, "publish_rolling", publish)
    assert backfill.run_backfill() == 0
    assert [c[0] for c in calls] == [day, day + timedelta(days=1), day + timedelta(days=1)]
    assert len(published) == 1


def test_equivalence_reuses_threshold_and_saves_only_complete_gemini_days(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from contextlib import contextmanager
    from types import SimpleNamespace
    from typing import Any

    day = date(2026, 10, 20)
    shared = {"arxiv_id": "synthetic-shared"}
    newer = {"arxiv_id": "synthetic-new"}
    sample = backfill.Sample(
        {day: [shared]}, {shared["arxiv_id"]: ["python"]}, {day: [shared, newer]}
    )
    monkeypatch.setattr(backfill.trend_fallback, "enabled", lambda: True)
    monkeypatch.setattr(backfill.trend_fallback, "model_label", lambda: "synthetic-model")
    monkeypatch.setattr(backfill.trend_store, "calibration", lambda _model: 0.5)
    monkeypatch.setattr(
        backfill.trend_fallback, "calibrated_threshold", lambda *_: pytest.fail("recalibrated")
    )
    monkeypatch.setattr(backfill, "load_sample", lambda *_: sample)
    monkeypatch.setattr(backfill, "_skills", lambda: [("python", "Python")])

    def similarities(papers: list[dict[str, str]], *_: Any, **__: Any) -> list[dict[str, float]]:
        assert papers == [shared, newer], "all fetched papers must be matched"
        return [{"python": 0.8}, {"python": 0.2}]

    monkeypatch.setattr(backfill.automatic_trends, "gemini_similarities", similarities)

    def compare(
        sample_arg: backfill.Sample, matched: dict[str, list[str]], threshold: float, *_: Any
    ) -> dict[str, object]:
        assert sample_arg.days == {day: [shared]}, "equivalence only compares common evidence"
        assert threshold == 0.5 and matched == {"synthetic-shared": ["python"], "synthetic-new": []}
        return {"passed": True, "model": "synthetic-model"}

    monkeypatch.setattr(backfill, "compare", compare)
    calls: list[tuple[dict[date, list[dict[str, str]]], dict[str, list[str]]]] = []
    monkeypatch.setattr(backfill.trend_store, "save_calibration", lambda *_: None)
    monkeypatch.setattr(
        backfill.trend_store,
        "save_days",
        lambda _conn, days, found, *_: calls.append((days, found)),
    )

    class Connection:
        def execute(self, _statement: str, _params: tuple[str]) -> Any:
            return SimpleNamespace(fetchone=lambda: (0.5,))

    @contextmanager
    def write_connection(_deadline: float):
        yield Connection()

    monkeypatch.setattr(backfill.repository, "write_connection", write_connection)
    monkeypatch.setattr(backfill, "SEED_DIR", tmp_path)
    monkeypatch.setattr(backfill, "REPORT", tmp_path / "equivalence.json")
    assert backfill.run_equivalence(28) == 0
    assert calls == [
        ({day: [shared, newer]}, {"synthetic-shared": ["python"], "synthetic-new": []})
    ]
    assert backfill.REPORT.is_file()


def test_equivalence_aborts_if_a_concurrent_run_saved_a_different_threshold(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from contextlib import contextmanager
    from types import SimpleNamespace
    from typing import Any

    day = date(2026, 10, 20)
    paper = {"arxiv_id": "synthetic-paper"}
    monkeypatch.setattr(backfill.trend_fallback, "enabled", lambda: True)
    monkeypatch.setattr(backfill.trend_fallback, "model_label", lambda: "synthetic-model")
    monkeypatch.setattr(backfill.trend_store, "calibration", lambda _model: None)
    monkeypatch.setattr(
        backfill,
        "load_sample",
        lambda *_: backfill.Sample({day: [paper]}, {paper["arxiv_id"]: ["python"]}, {day: [paper]}),
    )
    monkeypatch.setattr(backfill, "_skills", lambda: [("python", "Python")])
    monkeypatch.setattr(
        backfill.automatic_trends, "gemini_similarities", lambda *_a, **_k: [{"python": 0.7}]
    )
    monkeypatch.setattr(backfill.trend_fallback, "calibrated_threshold", lambda *_: 0.7)
    monkeypatch.setattr(
        backfill, "compare", lambda *_: {"passed": True, "model": "synthetic-model"}
    )
    monkeypatch.setattr(backfill.trend_store, "save_calibration", lambda *_: None)
    monkeypatch.setattr(
        backfill.trend_store, "save_days", lambda *_: pytest.fail("partial day saved")
    )

    class Connection:
        def execute(self, _statement: str, _params: tuple[str]) -> Any:
            return SimpleNamespace(fetchone=lambda: (0.6,))

    @contextmanager
    def write_connection(_deadline: float):
        yield Connection()

    monkeypatch.setattr(backfill.repository, "write_connection", write_connection)
    monkeypatch.setattr(backfill, "REPORT", tmp_path / "equivalence.json")
    with pytest.raises(SystemExit, match="Stored calibration changed"):
        backfill.run_equivalence(28)
    assert not backfill.REPORT.exists(), "a racing threshold must not produce a passing report"


def test_portable_export_rejects_unmeasured_or_inconsistent_history() -> None:
    from datetime import UTC, datetime

    first = backfill.automatic_trends.START_DAY
    last = datetime.now(UTC).date() - timedelta(days=backfill.automatic_trends.ARXIV_LAG_DAYS)
    days = [
        {
            "day": first + timedelta(days=i),
            "method": backfill.trend_store.GEMINI_METHOD,
            "papers": 1,
        }
        for i in range((last - first).days + 1)
    ]
    papers = [
        {"arxiv_id": f"synthetic-{i}", "published_on": row["day"], "method": row["method"]}
        for i, row in enumerate(days)
    ]
    assert backfill.validate_export(days, papers, backfill.trend_store.GEMINI_METHOD) == (
        first,
        last,
    )
    with pytest.raises(ValueError, match="No measured"):
        backfill.validate_export([], [], backfill.trend_store.GEMINI_METHOD)
    assert backfill.validate_export(days[:1], papers[:1], backfill.trend_store.GEMINI_METHOD) == (
        first,
        first,
    )
    assert backfill.validate_export(days[:-1], papers[:-1], backfill.trend_store.GEMINI_METHOD) == (
        first,
        last - timedelta(days=1),
    ), "a partial but measured range stays usable without claiming full history"
    with pytest.raises(ValueError, match="missing or out-of-order"):
        backfill.validate_export(
            days[:1] + days[2:], papers[:1] + papers[2:], backfill.trend_store.GEMINI_METHOD
        )
    with pytest.raises(ValueError, match="total differs"):
        backfill.validate_export(days, papers[:-1], backfill.trend_store.GEMINI_METHOD)
    with pytest.raises(ValueError, match="mix matching methods"):
        backfill.validate_export(
            days,
            [{**papers[0], "method": "other"}, *papers[1:]],
            backfill.trend_store.GEMINI_METHOD,
        )


def test_export_command_checks_explicit_database_before_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(backfill, "resolved_target", lambda: "localhost:5433/disposable")
    monkeypatch.setattr(backfill, "export_seed", lambda: pytest.fail("export read started"))
    with pytest.raises(SystemExit, match="Refusing to write"):
        backfill.main(["export-seed"])
