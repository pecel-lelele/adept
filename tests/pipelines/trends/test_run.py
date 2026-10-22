"""H01: the scheduled refresh only publishes valid snapshots and names the measured week."""

from datetime import date

from app.features.trends.provenance import window_from_note
from pipelines.trends import run, score


def _rows(ids: list[str]) -> list[dict]:
    return score.score_rows(
        {i: 1.0 for i in ids},
        100,
        {i: 2.0 for i in ids},
        100,
        {},
        {i: 0.5 for i in ids},
    )


def test_week_bounds() -> None:
    assert run.week_bounds("2026-W42") == (date(2026, 10, 12), date(2026, 10, 18))


def test_valid_snapshot_passes() -> None:
    ids = [f"s{i}" for i in range(run.MIN_SKILLS)]
    assert run.validate(_rows(ids), set(ids), "2026-W41", "2026-W42") == []


def test_broken_runs_are_refused() -> None:
    ids = [f"s{i}" for i in range(run.MIN_SKILLS)]
    rows = _rows(ids)
    assert any("one week" in e for e in run.validate(rows, set(ids), "2026-W42", "2026-W42"))
    assert any("at least" in e for e in run.validate(rows[:3], set(ids), "2026-W41", "2026-W42"))
    assert any("taxonomy" in e for e in run.validate(rows, set(ids[1:]), "2026-W41", "2026-W42"))
    rows[0]["velocity_fast"] = float("nan")
    assert any("non-finite" in e for e in run.validate(rows, set(ids), "2026-W41", "2026-W42"))


def test_provenance_names_only_the_days_actually_collected() -> None:
    """A Monday run collects one day: the note must not claim the rest of the week."""
    sources, note = run.provenance(
        "2026-W41",
        "2026-W42",
        (date(2026, 10, 5), date(2026, 10, 5)),
        (date(2026, 10, 12), date(2026, 10, 12)),
    )
    assert window_from_note(note) == (date(2026, 10, 12), date(2026, 10, 12))
    assert {s["retrieved_at"] for s in sources} == {"2026-10-12"}


def test_refresh_refuses_when_the_ingest_stored_nothing_new(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """An empty feed returns normally; older signals must not be republished as new."""
    from pipelines.trends import arxiv_ingest

    monkeypatch.setattr(arxiv_ingest, "main", lambda: None)
    stale = (date(2026, 10, 5), date(2026, 10, 12))
    monkeypatch.setattr(run, "collected_dates", lambda db_url, period=None: stale)
    published: list[object] = []
    monkeypatch.setattr(run, "publish", lambda *a, **k: published.append(a))
    assert run.main([]) == 1
    assert published == []
