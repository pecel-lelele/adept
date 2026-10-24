"""Remote MiniLM contract tests: no model download, database or paid endpoint."""

from __future__ import annotations

import httpx
import pytest

from pipelines.trends import encoder
from pipelines.trends.runpod import handler as worker

VECTOR = [1.0] + [0.0] * 383


def completed(count: int = 1) -> dict[str, object]:
    return {
        "status": "COMPLETED",
        "output": {
            "model": encoder.MODEL_ID,
            "revision": encoder.MODEL_REVISION,
            "dimensions": 384,
            "embeddings": [VECTOR] * count,
        },
    }


def transport(monkeypatch: pytest.MonkeyPatch, fn) -> None:
    real_client = httpx.Client
    monkeypatch.setattr(
        encoder.httpx,
        "Client",
        lambda **kw: real_client(
            transport=httpx.MockTransport(fn),
            **kw,
        ),
    )
    monkeypatch.setattr(encoder.time, "sleep", lambda _: None)


def test_sync_batches_preserve_input_order(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    sent = []

    def response(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.runpod.ai"
        assert request.headers["Authorization"] == "Bearer test-key"
        texts = json.loads(request.content)["input"]["texts"]
        sent.extend(texts)
        assert len(texts) <= 64
        return httpx.Response(200, json=completed(len(texts)))

    transport(monkeypatch, response)
    texts = [f"public sentence {i}" for i in range(70)]
    values = encoder.RunPodEncoder("endpoint-test", "test-key").encode(texts, batch_size=200)
    assert sent == texts and values == [VECTOR] * 70


def test_queued_cold_start_is_polled(monkeypatch: pytest.MonkeyPatch) -> None:
    paths = []

    def response(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(
            200,
            json=(
                {"id": "job-1", "status": "IN_QUEUE"} if request.method == "POST" else completed()
            ),
        )

    transport(monkeypatch, response)
    assert encoder.RunPodEncoder("endpoint", "key").encode(["public research"]) == [VECTOR]
    assert paths == ["/v2/endpoint/runsync", "/v2/endpoint/status/job-1"]


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED", "TIMED_OUT"])
def test_failed_job_is_not_a_valid_snapshot_input(monkeypatch, status: str) -> None:
    transport(monkeypatch, lambda _: httpx.Response(200, json={"status": status}))
    with pytest.raises(RuntimeError):
        encoder.RunPodEncoder("endpoint", "key").encode(["public sentence"])


def test_unknown_model_revision_is_rejected(monkeypatch) -> None:
    value = completed()
    value["output"]["revision"] = "different-weights"
    transport(monkeypatch, lambda _: httpx.Response(200, json=value))
    with pytest.raises(ValueError, match="incompatible"):
        encoder.RunPodEncoder("endpoint", "key").encode(["public sentence"])


@pytest.mark.parametrize("values", [[], [[0.0] * 384], [[float("nan")] * 384], [[1.0] * 768]])
def test_vector_shape_finiteness_and_count(values: object) -> None:
    with pytest.raises(ValueError):
        encoder.validate_vectors(values, 1)


@pytest.mark.parametrize("texts", [[], [""], ["x" * 4097], ["public text"] * 65, [42]])
def test_worker_rejects_invalid_input_before_loading_weights(monkeypatch, texts) -> None:
    monkeypatch.setattr(worker, "load_model", lambda: pytest.fail("invalid input loaded weights"))
    with pytest.raises(ValueError):
        worker.handler({"input": {"texts": texts}})


def test_runpod_configuration_needs_no_local_model(monkeypatch) -> None:
    monkeypatch.setenv("TRENDS_EMBEDDING_BACKEND", "runpod")
    monkeypatch.setenv("TRENDS_RUNPOD_ENDPOINT_ID", "endpoint")
    monkeypatch.setenv("TRENDS_RUNPOD_API_KEY", "test-key")
    encoder.get_encoder.cache_clear()
    try:
        assert isinstance(encoder.get_encoder(), encoder.RunPodEncoder)
    finally:
        encoder.get_encoder.cache_clear()


def test_endpoint_id_cannot_redirect_credentials() -> None:
    with pytest.raises(ValueError):
        encoder.RunPodEncoder("../../different-host", "key")


def test_default_requires_runpod_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRENDS_EMBEDDING_BACKEND", raising=False)
    monkeypatch.delenv("TRENDS_RUNPOD_ENDPOINT_ID", raising=False)
    monkeypatch.delenv("TRENDS_RUNPOD_API_KEY", raising=False)
    encoder.get_encoder.cache_clear()
    try:
        with pytest.raises(ValueError, match="TRENDS_RUNPOD_ENDPOINT_ID"):
            encoder.get_encoder()
    finally:
        encoder.get_encoder.cache_clear()
