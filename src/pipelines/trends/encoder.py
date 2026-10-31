"""RunPod MiniLM inference for background trend jobs; local CPU for development."""

from __future__ import annotations

import math
import os
import re
import sys
import time
from collections.abc import Callable, Sequence
from functools import lru_cache
from typing import Any, Protocol

import httpx

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DIMENSIONS = 384
MAX_BATCH = 64
# Whole-encode deadline: long enough for a cold worker (~80 s observed) plus several batches.
DEFAULT_TIMEOUT_S = 600.0
MAX_TIMEOUT_S = 900.0
# Each HTTP request is short; long waits happen between status polls, never inside one request.
REQUEST_TIMEOUT_S = 15.0
SUBMIT_ATTEMPTS = 3
SUBMIT_BACKOFF_S = 2.0
POLL_START_S = 1.0
POLL_MAX_S = 5.0
POLL_ERROR_LIMIT = 3
TRANSIENT_STATUS = frozenset({429, 500, 502, 503, 504})


class Encoder(Protocol):
    def encode(
        self, texts: Sequence[str], *, batch_size: int = 32, show_progress_bar: bool = False
    ) -> list[list[float]]: ...


def validate_vectors(value: object, count: int) -> list[list[float]]:
    """Fail closed before malformed or incompatible vectors reach cosine matching."""
    if not isinstance(value, list) or len(value) != count:
        raise ValueError("MiniLM returned the wrong number of vectors")
    vectors: list[list[float]] = []
    for row in value:
        if not isinstance(row, list) or len(row) != DIMENSIONS:
            raise ValueError("MiniLM must return 384-dimensional vectors")
        if any(type(n) not in (float, int) or not math.isfinite(n) for n in row):
            raise ValueError("MiniLM returned a non-finite or non-numeric vector")
        vector = [float(n) for n in row]
        if sum(n * n for n in vector) <= 0:
            raise ValueError("MiniLM returned a zero vector")
        vectors.append(vector)
    return vectors


class LocalEncoder:
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            MODEL_ID,
            revision=MODEL_REVISION,
            device="cpu",
            trust_remote_code=False,
        )

    def encode(
        self, texts: Sequence[str], *, batch_size: int = 32, show_progress_bar: bool = False
    ) -> list[list[float]]:
        if not texts:
            return []
        result = self.model.encode(
            list(texts),
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return validate_vectors(result.tolist(), len(texts))


class RunPodEncoder:
    """Remote MiniLM on RunPod Serverless.

    Jobs are submitted with ``POST /run`` (returns the job id at once) and then polled with
    short per-request timeouts. ``/runsync`` held the connection open while a cold worker
    booted (~80 s), longer than the client read timeout, so cold starts failed before a job id
    existed and the job could not be cancelled.
    """

    def __init__(
        self,
        endpoint_id: str,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT_S,
        *,
        deadline: float | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", endpoint_id) or not api_key:
            raise ValueError("Set TRENDS_RUNPOD_ENDPOINT_ID and TRENDS_RUNPOD_API_KEY")
        if not math.isfinite(timeout) or timeout <= 0 or timeout > MAX_TIMEOUT_S:
            raise ValueError("RunPod timeout must be between 0 and 900 seconds")
        self.url = f"https://api.runpod.ai/v2/{endpoint_id}"
        self.api_key = api_key
        self.timeout = timeout
        self.deadline = deadline
        self.cancelled = cancelled

    def _remaining(self, deadline: float) -> float:
        if self.cancelled and self.cancelled():
            raise TimeoutError("RunPod MiniLM operation cancelled")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("RunPod MiniLM inference exceeded its deadline")
        return remaining

    def _submit(self, client: httpx.Client, texts: list[str], deadline: float) -> dict[str, Any]:
        """Submit one job, retrying transient failures only while no job id was obtained."""
        for attempt in range(SUBMIT_ATTEMPTS):
            remaining = self._remaining(deadline)
            milliseconds = math.ceil(remaining * 1000)
            try:
                response = client.post(
                    f"{self.url}/run",
                    json={
                        "input": {"texts": texts},
                        # Provider minimums also bound orphan jobs if submission loses its ID.
                        "policy": {
                            "executionTimeout": max(5000, milliseconds),
                            "ttl": max(10000, milliseconds),
                        },
                    },
                    timeout=min(REQUEST_TIMEOUT_S, remaining),
                )
                if response.status_code in TRANSIENT_STATUS and attempt + 1 < SUBMIT_ATTEMPTS:
                    raise _TransientSubmitError(f"RunPod submit returned {response.status_code}")
                response.raise_for_status()
                result = response.json()
                if not isinstance(result, dict):
                    raise ValueError("RunPod returned an invalid submit response")
                return result
            except (httpx.ConnectError, httpx.ConnectTimeout, _TransientSubmitError):
                # Only failures that prove the POST never reached RunPod (or an explicit
                # 429/5xx refusal) are retried. A read timeout or mid-flight transport error
                # may follow an accepted job, and resubmitting would create a duplicate paid job.
                if attempt + 1 >= SUBMIT_ATTEMPTS:
                    raise
                time.sleep(min(SUBMIT_BACKOFF_S * (2**attempt), self._remaining(deadline)))
        raise AssertionError("unreachable")  # pragma: no cover

    def _poll(
        self, client: httpx.Client, job_id: str, result: dict[str, Any], deadline: float
    ) -> dict[str, Any]:
        """Poll until the job leaves the queue; transient poll errors are retried a few times."""
        interval = POLL_START_S
        failures = 0
        while result.get("status") in {"IN_QUEUE", "IN_PROGRESS"}:
            time.sleep(min(interval, self._remaining(deadline)))
            interval = min(POLL_MAX_S, interval * 1.5)
            remaining = self._remaining(deadline)
            try:
                response = client.get(
                    f"{self.url}/status/{job_id}", timeout=min(REQUEST_TIMEOUT_S, remaining)
                )
                response.raise_for_status()
                polled = response.json()
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                transient = not isinstance(exc, httpx.HTTPStatusError) or (
                    exc.response.status_code in TRANSIENT_STATUS
                )
                failures += 1
                if not transient or failures >= POLL_ERROR_LIMIT:
                    raise
                continue
            failures = 0
            if not isinstance(polled, dict):
                raise ValueError("RunPod returned an invalid status response")
            result = polled
        return result

    def _batch(self, texts: list[str], *, deadline: float | None = None) -> list[list[float]]:
        if deadline is None:
            deadline = time.monotonic() + self.timeout
        self._remaining(deadline)
        with httpx.Client(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=REQUEST_TIMEOUT_S,
            follow_redirects=False,
        ) as client:
            job_id: str | None = None
            completed = False
            try:
                result = self._submit(client, texts, deadline)
                candidate = result.get("id")
                if not isinstance(candidate, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", candidate):
                    raise ValueError("RunPod returned an invalid job id")
                job_id = candidate
                result = self._poll(client, job_id, result, deadline)
                completed = result.get("status") == "COMPLETED"
                if not completed:
                    raise RuntimeError(
                        "RunPod MiniLM job did not complete; snapshot will not publish"
                    )
                if time.monotonic() > deadline:
                    raise TimeoutError("RunPod MiniLM inference exceeded its deadline")
                output = result.get("output")
                if not isinstance(output, dict) or (
                    output.get("model") != MODEL_ID
                    or output.get("revision") != MODEL_REVISION
                    or output.get("dimensions") != DIMENSIONS
                ):
                    raise ValueError("RunPod returned an incompatible embedding model")
                return validate_vectors(output.get("embeddings"), len(texts))
            finally:
                if job_id is not None and not completed:
                    error = sys.exception()
                    try:
                        cancelled = client.post(f"{self.url}/cancel/{job_id}", timeout=2.0)
                        cancelled.raise_for_status()
                    except httpx.HTTPError:
                        if error is not None:
                            error.add_note(
                                "RunPod cancellation failed; the job policy remains bounded."
                            )

    def encode(
        self, texts: Sequence[str], *, batch_size: int = 32, show_progress_bar: bool = False
    ) -> list[list[float]]:
        size = min(MAX_BATCH, max(1, batch_size))
        vectors: list[list[float]] = []
        deadline = self.deadline or time.monotonic() + self.timeout
        for start in range(0, len(texts), size):
            vectors.extend(self._batch(list(texts[start : start + size]), deadline=deadline))
        return vectors


class _TransientSubmitError(Exception):
    """A retryable submit response (429 / 5xx) received before any job id."""


def configured_timeout() -> float:
    """Whole-encode deadline from TRENDS_RUNPOD_TIMEOUT_SECONDS (default 600, max 900)."""
    raw = os.environ.get("TRENDS_RUNPOD_TIMEOUT_SECONDS", "").strip()
    value = float(raw) if raw else DEFAULT_TIMEOUT_S
    if not math.isfinite(value) or value <= 0 or value > MAX_TIMEOUT_S:
        raise ValueError("TRENDS_RUNPOD_TIMEOUT_SECONDS must be between 0 and 900")
    return value


@lru_cache(maxsize=1)
def get_encoder() -> Encoder:
    backend = os.environ.get("TRENDS_EMBEDDING_BACKEND", "runpod").lower()
    if backend == "local":
        return LocalEncoder()
    if backend != "runpod":
        raise ValueError("TRENDS_EMBEDDING_BACKEND must be local or runpod")
    return RunPodEncoder(
        os.environ.get("TRENDS_RUNPOD_ENDPOINT_ID", ""),
        os.environ.get("TRENDS_RUNPOD_API_KEY", ""),
        configured_timeout(),
    )
