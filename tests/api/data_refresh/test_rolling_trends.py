"""Accumulated per-paper trend store and rolling 7-day snapshots (M1-018).

A fake in-memory store mirrors `trend_store`'s SQL semantics; arXiv and models are mocked.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from app.core import embeddings
from app.features.data_refresh import (
    automatic_trends,
    measurements,
    repository,
    service,
    trend_fallback,
    trend_store,
)

TODAY = datetime.now(UTC).date()
NEWEST = TODAY - timedelta(days=automatic_trends.ARXIV_LAG_DAYS)
STOP = SimpleNamespace(is_set=lambda: False, wait=lambda _seconds: False)


class Store:
    """In-memory stand-in for the three trend_store tables."""

    def __init__(self) -> None:
        self.days: dict[date, int] = {}
        self.fetched_on: dict[date, date] = {}
        self.papers: dict[str, tuple[date, str, str, list[str]]] = {}
        self.calibrations: dict[str, float] = {}

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            trend_store, "fetched_days", lambda: {d: self.fetched_on[d] for d in self.days}
        )
        monkeypatch.setattr(trend_store, "last_fetched", self.last_fetched)
        monkeypatch.setattr(trend_store, "calibration", self.calibrations.get)
        monkeypatch.setattr(trend_store, "minilm_rate", self.minilm_rate)
        monkeypatch.setattr(trend_store, "save_calibration", self.save_calibration)
        monkeypatch.setattr(trend_store, "save_days", self.save_days)
        monkeypatch.setattr(trend_store, "window", self.window)

    def minilm_rate(self) -> float | None:
        rows = [p for p in self.papers.values() if p[1] == "M1-014"]
        return sum(len(p[3]) for p in rows) / len(rows) if rows else None

    def save_calibration(self, _conn: Any, model: str, threshold: float, *_rest: Any) -> None:
        self.calibrations.setdefault(model, threshold)

    def last_fetched(self, start: date, end: date) -> date | None:
        dates = [on for d, on in self.fetched_on.items() if start <= d <= end]
        return max(dates) if dates else None

    def save_days(
        self, _conn: Any, days: Any, mentions: Any, method: str, model: str, on: date
    ) -> None:
        for day, papers in days.items():
            self.papers = {k: v for k, v in self.papers.items() if v[0] != day}
            self.days[day] = len(papers)
            self.fetched_on[day] = on
            for p in papers:
                self.papers.setdefault(
                    p["arxiv_id"], (day, method, model, mentions.get(p["arxiv_id"], []))
                )

    def window(self, start: date, end: date, ids: Any) -> Any:
        counts = dict.fromkeys(ids, 0)
        rows = [(k, v) for k, v in sorted(self.papers.items()) if start <= v[0] <= end]
        for _key, (_day, _method, _model, skills) in rows:
            for sid in skills:
                if sid in counts:
                    counts[sid] += 1
        total = sum(n for d, n in self.days.items() if start <= d <= end)
        sample = [{"id": k, "published_at": v[0].isoformat()} for k, v in rows]
        return counts, total, sample, sorted({v[2] for _k, v in rows})

    def fill(self, first: date, last: date, skills: list[str], model: str = "") -> None:
        model = model or automatic_trends.MODEL_ID
        day = first
        while day <= last:
            self.days[day] = 2
            self.fetched_on[day] = min(day + timedelta(days=automatic_trends.SETTLE_DAYS), TODAY)
            for n in range(2):
                self.papers[f"{day}-{n}"] = (day, "M1-014", model, skills)
            day += timedelta(days=1)


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Store:
    fake = Store()
    fake.install(monkeypatch)

    @contextmanager
    def writer(_deadline: float) -> Any:
        yield SimpleNamespace(execute=lambda *args: None)

    monkeypatch.setattr(repository, "write_connection", writer)
    monkeypatch.setattr(measurements, "load", lambda _day: None)
    monkeypatch.setattr(automatic_trends.refresh, "latest_published", lambda _url: None)
    monkeypatch.setattr(automatic_trends.refresh, "clear_trend_caches", lambda: None)
    return fake


def _published(monkeypatch: pytest.MonkeyPatch) -> list[measurements.MeasuredInputs]:
    out: list[measurements.MeasuredInputs] = []
    monkeypatch.setattr(measurements, "publish", lambda _c, inputs, _rows: out.append(inputs))
    return out


def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(automatic_trends, "fetch_window", lambda *a, **k: pytest.fail("network"))
    monkeypatch.setattr(
        automatic_trends, "RunPodEncoder", lambda *a, **k: pytest.fail("paid model call")
    )


def _arxiv(monkeypatch: pytest.MonkeyPatch, calls: list[date] | None = None) -> None:
    def fetch(start: date, end: date, deadline: float, **kwargs: Any) -> list[dict[str, str]]:
        assert start == end and kwargs["allow_empty"] and kwargs["limit"] == 50
        if calls is not None:
            calls.append(start)
        return [
            {
                "title": "Synthetic test paper",
                "abstract": "Synthetic sample only.",
                "arxiv_id": f"https://arxiv.org/abs/synthetic-{start}v2",
                "published_at": f"{start}T00:00:00Z",
            }
        ]

    monkeypatch.setattr(automatic_trends, "fetch_window", fetch)


def test_missing_days_are_oldest_first_bounded_and_never_include_unannounced_days() -> None:
    start = automatic_trends.START_DAY
    stored = {start: start + timedelta(days=automatic_trends.SETTLE_DAYS)}
    days = automatic_trends.missing_days(stored, TODAY)
    assert days[0] == automatic_trends.START_DAY + timedelta(days=1)
    assert len(days) <= automatic_trends.MAX_DAYS_PER_RUN
    assert all(d <= NEWEST for d in days)
    assert automatic_trends.paper_key("https://arxiv.org/abs/2410.11582v3") == "2410.11582"


def test_snapshot_window_needs_fourteen_consecutive_stored_days() -> None:
    end = date(2026, 10, 27)
    stored = {end - timedelta(days=i) for i in range(14)}
    assert automatic_trends.snapshot_end(stored) == end
    assert automatic_trends.snapshot_end(stored - {end - timedelta(days=5)}) is None


def test_current_trends_need_no_network_or_model(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.fill(automatic_trends.START_DAY, NEWEST, ["python"])
    current = (NEWEST - timedelta(days=6), NEWEST)
    note = f"Observed arXiv submissions {current[0]}..{current[1]} against older days."
    monkeypatch.setattr(automatic_trends.refresh, "latest_published", lambda _url: (NEWEST, note))
    previous = (current[0] - timedelta(days=7), current[0] - timedelta(days=1))
    published = automatic_trends.rolling_inputs(previous, current, TODAY - timedelta(days=1))
    monkeypatch.setattr(measurements, "load", lambda _day: published)
    _no_network(monkeypatch)
    result = automatic_trends.run(time.monotonic(), 600, STOP)
    assert result.rows_upserted == 0 and "current through" in result.message


def test_stored_papers_rebuild_a_rolling_snapshot_without_network(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.fill(automatic_trends.START_DAY, NEWEST, ["python"])
    published = _published(monkeypatch)
    _no_network(monkeypatch)
    result = automatic_trends.run(time.monotonic(), 600, STOP)
    inputs = published[0]
    assert result.rows_upserted > 0
    assert inputs.method == "M1-018" and inputs.current == (NEWEST - timedelta(days=6), NEWEST)
    assert inputs.previous[1] + timedelta(days=1) == inputs.current[0]
    assert inputs.total_after == 14 and inputs.counts_after["python"] == 14
    assert "rolling 7-day windows" in inputs.note and "fallback" not in inputs.note


def test_refresh_fetches_only_new_days_and_matches_each_paper_once(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.fill(automatic_trends.START_DAY, NEWEST - timedelta(days=2), ["python"])
    calls: list[date] = []
    _arxiv(monkeypatch, calls)
    monkeypatch.setenv("TRENDS_RUNPOD_ENDPOINT_ID", "synthetic-endpoint")
    monkeypatch.setenv("TRENDS_RUNPOD_API_KEY", "synthetic-test-key")
    encoded: list[int] = []

    class Encoder:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
            encoded.append(len(texts))
            return [[1.0] * 384 for _ in texts]

    monkeypatch.setattr(automatic_trends, "RunPodEncoder", Encoder)
    published = _published(monkeypatch)
    automatic_trends.run(time.monotonic(), 600, STOP)
    assert calls == [NEWEST - timedelta(days=1), NEWEST]
    assert store.papers[f"synthetic-{NEWEST}"][1] == "M1-014"  # version suffix dropped
    assert published[0].current[1] == NEWEST
    # A second refresh finds nothing new: no fetch, no model.
    _no_network(monkeypatch)
    monkeypatch.setattr(
        automatic_trends.refresh,
        "latest_published",
        lambda _url: (NEWEST, published[0].note),
    )
    monkeypatch.setattr(measurements, "load", lambda _day: published[0])
    assert "current through" in automatic_trends.run(time.monotonic(), 600, STOP).message


def _gemini(monkeypatch: pytest.MonkeyPatch, dims: list[int]) -> None:
    def embed(texts: list[str], *args: Any, dims: int, **kwargs: Any) -> list[list[float]]:
        assert kwargs["timeout_s"] > 0
        _gemini_dims.append(dims)
        return [[1.0] + [0.0] * (dims - 1) for _ in texts]

    _gemini_dims = dims
    monkeypatch.setattr(trend_fallback, "enabled", lambda: True)
    monkeypatch.setattr(embeddings, "embed", embed)


@pytest.mark.parametrize("runpod", ["failed", "missing", "bad-settings"])
def test_gemini_fallback_at_minilm_size_is_calibrated_once_and_labelled(
    store: Store, monkeypatch: pytest.MonkeyPatch, runpod: str
) -> None:
    store.fill(automatic_trends.START_DAY, NEWEST - timedelta(days=1), ["python"])
    _arxiv(monkeypatch)
    dims: list[int] = []
    _gemini(monkeypatch, dims)
    if runpod != "missing":
        monkeypatch.setenv("TRENDS_RUNPOD_ENDPOINT_ID", "synthetic-endpoint")
        monkeypatch.setenv("TRENDS_RUNPOD_API_KEY", "synthetic-test-key")

        class Down:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                if runpod == "bad-settings":
                    raise ValueError("Set TRENDS_RUNPOD_ENDPOINT_ID and TRENDS_RUNPOD_API_KEY")

            def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
                raise TimeoutError("RunPod MiniLM inference exceeded its deadline")

        monkeypatch.setattr(automatic_trends, "RunPodEncoder", Down)
    published = _published(monkeypatch)
    automatic_trends.run(time.monotonic(), 600, STOP)
    assert set(dims) == {384}  # same vector size as MiniLM
    model = trend_fallback.model_label()
    assert model.endswith("@384") and model in store.calibrations
    assert store.papers[f"synthetic-{NEWEST}"][1:3] == ("M1-017", model)
    assert "Gemini fallback calibrated" in published[0].note
    assert published[0].model_revision == "mixed"


def test_fallback_without_minilm_evidence_keeps_the_last_snapshot(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arxiv(monkeypatch)
    _gemini(monkeypatch, [])
    monkeypatch.setattr(measurements, "load_minilm_reference", lambda _day: None)
    published = _published(monkeypatch)
    with pytest.raises(service.RefreshFailed) as failed:
        automatic_trends.run(time.monotonic(), 600, STOP)
    assert failed.value.code == "refresh_not_supported"
    assert published == [] and store.days == {}


def test_nothing_configured_is_reported_before_any_fetch(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(trend_fallback, "enabled", lambda: False)
    _no_network(monkeypatch)
    with pytest.raises(service.RefreshFailed) as failed:
        automatic_trends.run(time.monotonic(), 600, STOP)
    assert failed.value.code == "refresh_not_configured"


def test_missing_store_migration_stops_before_paid_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import psycopg

    class Missing:
        def execute(self, *args: Any) -> None:
            raise psycopg.errors.UndefinedTable("Synthetic schema absence")

    @contextmanager
    def connection() -> Any:
        yield Missing()

    monkeypatch.setattr(trend_store, "connection", connection)
    _no_network(monkeypatch)
    with pytest.raises(service.RefreshFailed, match="migration"):
        automatic_trends.run(time.monotonic(), 60, STOP)


def test_settle_days_refetch_an_early_fetched_day_exactly_once() -> None:
    day = TODAY - timedelta(days=automatic_trends.SETTLE_DAYS)
    early = day + timedelta(days=automatic_trends.ARXIV_LAG_DAYS)
    settled = day + timedelta(days=automatic_trends.SETTLE_DAYS)
    full = {
        d: d + timedelta(days=automatic_trends.SETTLE_DAYS)
        for d in (
            automatic_trends.START_DAY + timedelta(days=i)
            for i in range((TODAY - automatic_trends.START_DAY).days)
        )
    }
    assert day in automatic_trends.missing_days({**full, day: early}, TODAY)
    assert day not in automatic_trends.missing_days({**full, day: settled}, TODAY)
    # Not settled yet: an early fetch stays until its settle date.
    recent = NEWEST
    assert recent not in automatic_trends.missing_days({**full, recent: TODAY}, TODAY)


def test_refetched_day_replaces_its_papers_and_republishes(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.fill(automatic_trends.START_DAY, NEWEST, ["python"])
    day = TODAY - timedelta(days=automatic_trends.SETTLE_DAYS)
    store.fetched_on[day] = day + timedelta(days=automatic_trends.ARXIV_LAG_DAYS)
    calls: list[date] = []
    _arxiv(monkeypatch, calls)
    monkeypatch.setenv("TRENDS_RUNPOD_ENDPOINT_ID", "synthetic-endpoint")
    monkeypatch.setenv("TRENDS_RUNPOD_API_KEY", "synthetic-test-key")

    class Encoder:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
            return [[1.0] * 384 for _ in texts]

    monkeypatch.setattr(automatic_trends, "RunPodEncoder", Encoder)
    current = (NEWEST - timedelta(days=6), NEWEST)
    note = f"Observed arXiv submissions {current[0]}..{current[1]} against older days."
    monkeypatch.setattr(automatic_trends.refresh, "latest_published", lambda _url: (NEWEST, note))
    published = _published(monkeypatch)
    automatic_trends.run(time.monotonic(), 600, STOP)
    assert calls == [day]
    assert store.days[day] == 1 and store.fetched_on[day] == TODAY
    assert [k for k, v in store.papers.items() if v[0] == day] == [f"synthetic-{day}"]
    assert published, "a refetched day inside the windows must republish"


@pytest.mark.parametrize("age", [5, 12])
@pytest.mark.parametrize("failure_stage", ["rows", "publish"])
def test_retry_republishes_corrected_counts_after_a_failed_refresh(
    store: Store, monkeypatch: pytest.MonkeyPatch, age: int, failure_stage: str
) -> None:
    store.fill(automatic_trends.START_DAY, NEWEST, ["python"])
    day = TODAY - timedelta(days=age)
    store.fetched_on[day] = day + timedelta(days=automatic_trends.ARXIV_LAG_DAYS)
    current = (NEWEST - timedelta(days=6), NEWEST)
    previous = (current[0] - timedelta(days=7), current[0] - timedelta(days=1))
    original = automatic_trends.rolling_inputs(previous, current, TODAY)
    monkeypatch.setattr(
        automatic_trends.refresh, "latest_published", lambda _url: (NEWEST, original.note)
    )
    monkeypatch.setattr(measurements, "load", lambda _day: original)
    calls: list[date] = []
    _arxiv(monkeypatch, calls)
    monkeypatch.setattr(automatic_trends, "_runpod", lambda: ("synthetic", "synthetic"))
    monkeypatch.setattr(
        automatic_trends,
        "match",
        lambda papers, *args: (
            [["python"] for _ in papers],
            "M1-014",
            automatic_trends.MODEL_ID,
            None,
        ),
    )
    published = _published(monkeypatch)

    def fail(*args: Any) -> None:
        raise TimeoutError("Synthetic failure after committing corrected papers")

    with monkeypatch.context() as failing:
        failing.setattr(measurements, failure_stage, fail)
        with pytest.raises(TimeoutError, match="Synthetic failure"):
            automatic_trends.run(time.monotonic(), 600, STOP)

    assert calls == [day] and published == []
    assert store.days[day] == 1 and store.fetched_on[day] == TODAY
    assert automatic_trends.missing_days(store.fetched_on, TODAY) == []
    _no_network(monkeypatch)
    monkeypatch.setattr(automatic_trends, "match", lambda *args: pytest.fail("rematched papers"))
    result = automatic_trends.run(time.monotonic(), 600, STOP)

    assert result.rows_upserted > 0 and len(published) == 1
    corrected = published[0]
    assert corrected.current == original.current and corrected.fetched == original.fetched
    if day >= current[0]:
        assert original.counts_after["python"] == original.total_after == 14
        assert corrected.counts_after["python"] == corrected.total_after == 13
        assert corrected.counts_before == original.counts_before
    else:
        assert original.counts_before["python"] == original.total_before == 14
        assert corrected.counts_before["python"] == corrected.total_before == 13
        assert corrected.counts_after == original.counts_after
    monkeypatch.setattr(measurements, "load", lambda _day: corrected)
    assert automatic_trends.run(time.monotonic(), 600, STOP).rows_upserted == 0
    assert len(published) == 1


def test_rebuild_reports_the_stored_fetch_date_not_today(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every stored day settled; the newest was fetched yesterday, and nothing is new today.
    last = TODAY - timedelta(days=automatic_trends.SETTLE_DAYS + 1)
    store.fill(automatic_trends.START_DAY, last, ["python"])
    monkeypatch.setattr(automatic_trends, "missing_days", lambda _stored, _today: [])
    fetched = last + timedelta(days=automatic_trends.SETTLE_DAYS)
    published = _published(monkeypatch)
    _no_network(monkeypatch)
    automatic_trends.run(time.monotonic(), 600, STOP)
    inputs = published[0]
    assert inputs.fetched == fetched
    arxiv = next(s for s in inputs.sources if "arXiv" in s.name)
    assert str(arxiv.retrieved_at) == fetched.isoformat()
    assert f"last fetched {fetched}" in inputs.note
