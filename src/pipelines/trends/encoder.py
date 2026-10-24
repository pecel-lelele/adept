"""RunPod MiniLM inference for background trend jobs; local CPU for development."""

from __future__ import annotations

import math
import os
import re
import time
from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

import httpx

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DIMENSIONS = 384
MAX_BATCH = 64


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
    def __init__(self, endpoint_id: str, api_key: str, timeout: float = 120) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", endpoint_id) or not api_key:
            raise ValueError("Set TRENDS_RUNPOD_ENDPOINT_ID and TRENDS_RUNPOD_API_KEY")
        if not math.isfinite(timeout) or timeout <= 0 or timeout > 900:
            raise ValueError("RunPod timeout must be between 0 and 900 seconds")
        self.url = f"https://api.runpod.ai/v2/{endpoint_id}"
        self.api_key = api_key
        self.timeout = timeout

    def _batch(self, texts: list[str]) -> list[list[float]]:
        deadline = time.monotonic() + self.timeout
        with httpx.Client(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=min(30, self.timeout),
            follow_redirects=False,
        ) as client:
            response = client.post(f"{self.url}/runsync", json={"input": {"texts": texts}})
            response.raise_for_status()
            result = response.json()
            while result.get("status") in {"IN_QUEUE", "IN_PROGRESS"}:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("RunPod MiniLM inference exceeded its deadline")
                job_id = result.get("id", "")
                if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", job_id):
                    raise ValueError("RunPod returned an invalid job id")
                time.sleep(min(1, remaining))
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("RunPod MiniLM inference exceeded its deadline")
                response = client.get(f"{self.url}/status/{job_id}", timeout=min(30, remaining))
                response.raise_for_status()
                result = response.json()
        if result.get("status") != "COMPLETED":
            raise RuntimeError("RunPod MiniLM job did not complete; snapshot will not publish")
        output = result.get("output")
        if not isinstance(output, dict) or (
            output.get("model") != MODEL_ID
            or output.get("revision") != MODEL_REVISION
            or output.get("dimensions") != DIMENSIONS
        ):
            raise ValueError("RunPod returned an incompatible embedding model")
        return validate_vectors(output.get("embeddings"), len(texts))

    def encode(
        self, texts: Sequence[str], *, batch_size: int = 32, show_progress_bar: bool = False
    ) -> list[list[float]]:
        size = min(MAX_BATCH, max(1, batch_size))
        vectors: list[list[float]] = []
        for start in range(0, len(texts), size):
            vectors.extend(self._batch(list(texts[start : start + size])))
        return vectors


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
        float(os.environ.get("TRENDS_RUNPOD_TIMEOUT_SECONDS", "120")),
    )
