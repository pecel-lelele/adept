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
    assert backfill.verdict(0.6, 0.7, 0.7, 500)
    assert not backfill.verdict(0.59, 0.9, 0.9, 900)
    assert not backfill.verdict(0.9, 0.69, 0.9, 900)
    assert not backfill.verdict(0.9, 0.9, 0.69, 900)
    assert not backfill.verdict(0.9, 0.9, 0.9, 499)


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
