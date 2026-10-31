"""Text embeddings for cosine-similarity matching (Core, M4).

One entry point, `embed(texts, task)`, returning unit-length vectors or raising
`EmbeddingsUnavailable`. Callers must work without it (exact catalogue matching stays the
baseline). Every text is PII-redacted before it leaves the API, and callers send short
phrases only (catalogue labels, skills-list entries), never a whole CV.

Provider: Google Gemini `gemini-embedding-001` through the Generative Language REST API,
768 dimensions (Matryoshka-truncated, then re-normalised), task type SEMANTIC_SIMILARITY.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from typing import Literal

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security.pii import redact_text

log = get_logger("app.embeddings")

DIMS = 768
BATCH = 100
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
Task = Literal["SEMANTIC_SIMILARITY", "RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"]

# After a failure, fail fast for this long instead of making every request wait for a timeout.
COOLDOWN_S = 60.0
_down_until = 0.0


class EmbeddingsUnavailable(RuntimeError):
    """No provider configured, no key, or the provider failed; use the non-embedding path."""


def enabled() -> bool:
    s = get_settings()
    return s.embeddings_provider == "gemini" and bool(s.gemini_api_key)


def model_name() -> str:
    return f"{get_settings().embeddings_model}@{DIMS}"


def _unit(v: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def embed(
    texts: Sequence[str],
    task: Task = "SEMANTIC_SIMILARITY",
    patient: bool = False,
    timeout_s: float | None = None,
    dims: int = DIMS,
) -> list[list[float]]:
    """Unit vectors for `texts`, in order. Raises EmbeddingsUnavailable on any problem.

    `patient` (catalogue indexing only, never a user request) waits out rate limits (HTTP 429)
    in small batches instead of failing at once. `timeout_s` caps the HTTP timeout below the
    configured one (callers with their own deadline pass the time they have left). `dims` sets the
    Matryoshka output size (trend fallback uses 384, MiniLM's size)."""
    global _down_until  # noqa: PLW0603
    if not texts:
        return []
    if not enabled():
        raise EmbeddingsUnavailable("Embeddings are off (EMBEDDINGS_PROVIDER / GEMINI_API_KEY).")
    if time.monotonic() < _down_until:
        raise EmbeddingsUnavailable("Embeddings provider failed recently; retrying shortly.")
    s = get_settings()
    url = GEMINI_URL.format(model=s.embeddings_model)
    out: list[list[float]] = []
    try:
        timeout = (
            s.embeddings_timeout_s if timeout_s is None else min(s.embeddings_timeout_s, timeout_s)
        )
        with httpx.Client(timeout=timeout) as client:
            size = 20 if patient else BATCH
            for i in range(0, len(texts), size):
                chunk = [redact_text(t)[:2000] for t in texts[i : i + size]]
                for attempt in range(6 if patient else 1):
                    r = client.post(
                        url,
                        headers={"x-goog-api-key": s.gemini_api_key},
                        json={
                            "requests": [
                                {
                                    "model": f"models/{s.embeddings_model}",
                                    "content": {"parts": [{"text": t}]},
                                    "taskType": task,
                                    "outputDimensionality": dims,
                                }
                                for t in chunk
                            ]
                        },
                    )
                    if r.status_code != 429 or not patient:
                        break
                    wait = float(r.headers.get("retry-after") or 20 * (attempt + 1))
                    log.info("embeddings rate-limited; waiting %.0fs", wait)
                    time.sleep(min(wait, 90))
                r.raise_for_status()
                out.extend(_unit(e["values"]) for e in r.json()["embeddings"])
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        _down_until = time.monotonic() + COOLDOWN_S
        # Never log the response body or headers: they could echo the key.
        log.warning("embeddings call failed: %s", type(exc).__name__)
        raise EmbeddingsUnavailable(str(type(exc).__name__)) from exc
    if len(out) != len(texts) or any(len(v) != dims for v in out):
        raise EmbeddingsUnavailable("Unexpected embedding response shape.")
    return out


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity of two unit vectors."""
    return sum(x * y for x, y in zip(a, b, strict=True))
