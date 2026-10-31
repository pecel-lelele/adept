"""On-demand trend refresh keeps working without RunPod: calibrated Gemini fallback (M1-017)."""

from __future__ import annotations

import time
from typing import Any

import pytest

from app.core import embeddings
from app.features.data_refresh import trend_fallback

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
