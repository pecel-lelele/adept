"""Gemini fallback for the on-demand trend refresh when the RunPod MiniLM worker is unavailable.

Method (M1-017, stored per paper by M1-018). MiniLM's 0.55 sentence threshold does not
transfer to another model's cosine scale, so the fallback never reuses it:

1. Embed each paper once (title + abstract) and each skill label with Gemini at 384
   dimensions, MiniLM's size (`app.core.embeddings`, SEMANTIC_SIMILARITY). Equal size keeps
   storage uniform; the two models' vectors are still never compared with each other.
2. Score paper x skill by cosine similarity.
3. Calibrate one threshold, once per model, from stored MiniLM evidence: the threshold
   reproduces MiniLM's mentions per paper on the first fallback batch, then is stored and
   reused, so later batches keep real changes in mention volume.

Without stored MiniLM evidence there is nothing to calibrate against, and the refresh fails
instead of guessing (the last good snapshot stays live).
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence

from app.core import embeddings

# One request per batch; checking the deadline between batches bounds the whole call.
BATCH = 100
DIMS = 384  # MiniLM's vector size


class FallbackUnavailable(RuntimeError):
    """Gemini is off, failed, or there is no stored measurement to calibrate against."""


def enabled() -> bool:
    return embeddings.enabled()


def model_label() -> str:
    return f"{embeddings.get_settings().embeddings_model}@{DIMS}"


def embed_bounded(
    texts: Sequence[str], deadline: float, cancelled: Callable[[], bool] = lambda: False
) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        if cancelled():
            raise TimeoutError("refresh cancelled")
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("refresh time budget reached")
        try:
            # The request may not outlive the refresh deadline (that time is kept for saving).
            out.extend(embeddings.embed(texts[i : i + BATCH], timeout_s=left, dims=DIMS))
        except embeddings.EmbeddingsUnavailable as exc:
            raise FallbackUnavailable(str(exc)) from exc
        if time.monotonic() >= deadline:
            raise TimeoutError("refresh time budget reached")
    return out


def paper_text(paper: dict[str, str]) -> str:
    return f"{paper['title']}. {paper['abstract']}"


def similarities(
    paper_vectors: Sequence[Sequence[float]], skill_vectors: dict[str, Sequence[float]]
) -> list[dict[str, float]]:
    """Per paper, cosine similarity to every skill."""
    return [
        {sid: embeddings.cosine(vec, sv) for sid, sv in skill_vectors.items()}
        for vec in paper_vectors
    ]


def mentions_per_paper(counts: dict[str, int], papers: int) -> float:
    return sum(counts.values()) / papers if papers > 0 else 0.0


def calibrated_threshold(sims: Sequence[dict[str, float]], rate: float) -> float:
    """Smallest threshold whose mention count on `sims` reaches `rate` mentions per paper."""
    values = sorted((v for row in sims for v in row.values()), reverse=True)
    target = round(rate * len(sims))
    if not values or target <= 0:
        return math.inf  # the reference measured no mentions: count none
    return values[min(target, len(values)) - 1]


def count(sims: Sequence[dict[str, float]], threshold: float) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in sims:
        for sid, value in row.items():
            out[sid] = out.get(sid, 0) + (value >= threshold)
    return out


def mentions(sims: Sequence[dict[str, float]], threshold: float) -> list[list[str]]:
    """Per paper, the skills at or above the threshold."""
    return [sorted(sid for sid, value in row.items() if value >= threshold) for row in sims]
