"""RunPod queue-based worker. Receives public research text or catalogue skill labels."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

from pipelines.trends.encoder import (
    DIMENSIONS,
    MAX_BATCH,
    MODEL_ID,
    MODEL_REVISION,
    validate_vectors,
)

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


def parse_input(job: dict[str, object]) -> list[str]:
    payload = job.get("input")
    texts = payload.get("texts") if isinstance(payload, dict) else None
    if not isinstance(texts, list) or not 1 <= len(texts) <= MAX_BATCH:
        raise ValueError("input.texts must contain 1 to 64 strings")
    if any(not isinstance(t, str) or not t.strip() or len(t) > 4096 for t in texts):
        raise ValueError("Each text must be non-empty and at most 4096 characters")
    return texts


@lru_cache(maxsize=1)
def load_model() -> SentenceTransformer:
    import torch
    from sentence_transformers import SentenceTransformer

    device = os.environ.get("MINILM_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    return SentenceTransformer(
        os.environ.get("MINILM_MODEL_PATH", "/opt/minilm"),
        device=device,
        local_files_only=True,
    )


def handler(job: dict[str, object]) -> dict[str, object]:
    texts = parse_input(job)
    values = load_model().encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return {
        "model": MODEL_ID,
        "revision": MODEL_REVISION,
        "dimensions": DIMENSIONS,
        "embeddings": validate_vectors(values.tolist(), len(texts)),
    }


if __name__ == "__main__":
    import runpod

    load_model()
    runpod.serverless.start({"handler": handler})
