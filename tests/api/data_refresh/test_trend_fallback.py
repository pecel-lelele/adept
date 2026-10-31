"""On-demand trend refresh keeps working without RunPod: calibrated Gemini fallback (M1-017)."""

from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from app.core import embeddings
from app.features.data_refresh import automatic_trends, repository, service, trend_fallback

PAPER = {
    "title": "Synthetic test paper",
    "abstract": "Synthetic sample only.",
    "arxiv_id": "https://arxiv.org/abs/synthetic-fixture",
}


def test_threshold_reproduces_the_stored_mention_rate() -> None:
    sims = [{"a": 0.9, "b": 0.2}, {"a": 0.8, "b": 0.7}, {"a": 0.1, "b": 0.3}]
    # 1 mention per paper -> the 3 strongest pairs count.
    threshold = trend_fallback.calibrated_threshold(sims, 1.0)
    assert threshold == 0.7
    assert sum(trend_fallback.count(sims, threshold).values()) == 3
    assert trend_fallback.calibrated_threshold(sims, 0.0) == float("inf")
    assert trend_fallback.mentions_per_paper({"a": 4, "b": 2}, 3) == 2.0


def test_embedding_calls_stop_at_the_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embeddings, "embed", lambda texts, *a, **k: pytest.fail("called late"))
    with pytest.raises(TimeoutError):
        trend_fallback.embed_bounded(["x"], time.monotonic() - 1)


def test_each_embedding_request_is_capped_by_the_time_left(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[float] = []

    def slow(texts: list[str], *args: Any, timeout_s: float, **kwargs: Any) -> list[list[float]]:
        seen.append(timeout_s)
        time.sleep(0.06)  # the request returns after the deadline
        return [[1.0] for _ in texts]

    monkeypatch.setattr(embeddings, "embed", slow)
    with pytest.raises(TimeoutError):
        trend_fallback.embed_bounded(["x"] * 150, time.monotonic() + 0.05)
    assert len(seen) == 1 and 0 < seen[0] <= 0.05


def _setup(monkeypatch: pytest.MonkeyPatch, *, runpod: bool, reference: object | None) -> list[Any]:
    published: list[Any] = []

    @contextmanager
    def connection(deadline: float) -> Any:
        yield SimpleNamespace(execute=lambda *args: None)

    monkeypatch.setattr(automatic_trends.refresh, "latest_published", lambda _url: None)
    # No stored inputs for the current week; calibration may only read a MiniLM week.
    monkeypatch.setattr(automatic_trends.measurements, "load", lambda *a, **k: None)
    monkeypatch.setattr(
        automatic_trends.measurements, "load_minilm_reference", lambda _day: reference
    )
    monkeypatch.setattr(
        automatic_trends,
        "fetch_window",
        lambda *args: [{**PAPER, "published_at": args[0].isoformat() + "T00:00:00Z"}],
    )
    monkeypatch.setattr(repository, "write_connection", connection)
    monkeypatch.setattr(
        automatic_trends.measurements,
        "publish",
        lambda _c, inputs, _r: published.append(inputs),
    )
    monkeypatch.setattr(automatic_trends.refresh, "clear_trend_caches", lambda: None)
    monkeypatch.setattr(trend_fallback, "enabled", lambda: True)
    monkeypatch.setattr(trend_fallback, "model_label", lambda: "gemini-embedding-001@768")
    monkeypatch.setattr(embeddings, "embed", lambda texts, *a, **k: [[1.0, 0.0] for _ in texts])
    if runpod:
        monkeypatch.setenv("TRENDS_RUNPOD_ENDPOINT_ID", "synthetic-endpoint")
        monkeypatch.setenv("TRENDS_RUNPOD_API_KEY", "synthetic-test-key")

        class DownEncoder:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.deadline = kwargs["deadline"]

            def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
                raise TimeoutError("RunPod MiniLM inference exceeded its deadline")

        monkeypatch.setattr(automatic_trends, "RunPodEncoder", DownEncoder)
    else:
        monkeypatch.setattr(
            automatic_trends, "RunPodEncoder", lambda *a, **k: pytest.fail("RunPod not configured")
        )
    return published


REFERENCE = SimpleNamespace(
    counts_after={"python": 10_000}, total_after=1, current=(date(2026, 10, 5), date(2026, 10, 11))
)
STOP = SimpleNamespace(is_set=lambda: False, wait=lambda _seconds: False)


@pytest.mark.parametrize("runpod", [True, False], ids=["runpod-failed", "runpod-missing"])
def test_refresh_falls_back_to_gemini_and_labels_the_method(
    monkeypatch: pytest.MonkeyPatch, runpod: bool
) -> None:
    published = _setup(monkeypatch, runpod=runpod, reference=REFERENCE)
    result = automatic_trends.run(time.monotonic(), 600, STOP)
    assert result.rows_upserted > 0
    inputs = published[0]
    assert inputs.method == "M1-017"
    assert inputs.model == "gemini-embedding-001@768"
    assert "MiniLM cosine method" not in inputs.note
    assert "fallback" in inputs.note


def test_bad_worker_settings_still_reach_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    published = _setup(monkeypatch, runpod=True, reference=REFERENCE)

    def bad_endpoint(*args: Any, **kwargs: Any) -> None:
        raise ValueError("Set TRENDS_RUNPOD_ENDPOINT_ID and TRENDS_RUNPOD_API_KEY")

    monkeypatch.setattr(automatic_trends, "RunPodEncoder", bad_endpoint)
    automatic_trends.run(time.monotonic(), 600, STOP)
    assert published[0].method == "M1-017"


def test_fallback_without_a_stored_measurement_keeps_the_last_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    published = _setup(monkeypatch, runpod=False, reference=None)
    with pytest.raises(service.RefreshFailed) as failed:
        automatic_trends.run(time.monotonic(), 600, STOP)
    assert failed.value.code == "refresh_not_supported"
    assert published == []


def test_no_runpod_and_no_gemini_is_reported_as_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _setup(monkeypatch, runpod=False, reference=REFERENCE)
    monkeypatch.setattr(trend_fallback, "enabled", lambda: False)
    with pytest.raises(service.RefreshFailed) as failed:
        automatic_trends.run(time.monotonic(), 600, STOP)
    assert failed.value.code == "refresh_not_configured"
