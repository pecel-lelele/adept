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


class FakeRunPod:
    """In-memory RunPod: /run queues a job; /status answers from a scripted list."""

    def __init__(self, statuses: list[dict[str, object]] | None = None) -> None:
        self.paths: list[str] = []
        self.submitted: list[list[str]] = []
        self.statuses = statuses
        self.jobs: dict[str, int] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        import json

        self.paths.append(request.url.path)
        assert request.url.host == "api.runpod.ai"
        assert request.headers["Authorization"] == "Bearer test-key"
        if request.url.path.endswith("/run"):
            texts = json.loads(request.content)["input"]["texts"]
            self.submitted.append(texts)
            job = f"job-{len(self.submitted)}"
            self.jobs[job] = len(texts)
            return httpx.Response(200, json={"id": job, "status": "IN_QUEUE"})
        if "/cancel/" in request.url.path:
            return httpx.Response(200, json={"status": "CANCELLED"})
        job = request.url.path.rsplit("/", 1)[-1]
        if self.statuses:
            return httpx.Response(200, json=self.statuses.pop(0))
        return httpx.Response(200, json=completed(self.jobs[job]))


def test_batches_preserve_input_order(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRunPod()
    transport(monkeypatch, fake)
    texts = [f"public sentence {i}" for i in range(70)]
    values = encoder.RunPodEncoder("endpoint-test", "test-key").encode(texts, batch_size=200)
    assert [t for batch in fake.submitted for t in batch] == texts
    assert all(len(batch) <= 64 for batch in fake.submitted)
    assert values == [VECTOR] * 70


def test_cold_start_is_submitted_async_and_polled(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cold worker keeps the job IN_QUEUE for many polls; no request waits for the boot."""
    queued = [{"id": "job-1", "status": "IN_QUEUE"}] * 6 + [{"status": "IN_PROGRESS"}]
    fake = FakeRunPod(statuses=[*queued, completed()])
    transport(monkeypatch, fake)
    assert encoder.RunPodEncoder("endpoint", "test-key").encode(["public research"]) == [VECTOR]
    assert fake.paths[0] == "/v2/endpoint/run"
    assert fake.paths[1:] == ["/v2/endpoint/status/job-1"] * 8
    assert "/v2/endpoint/runsync" not in fake.paths


def test_submit_connect_failure_and_5xx_are_retried_without_a_duplicate_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeRunPod()
    attempts = []

    def flaky(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/run"):
            attempts.append(request.url.path)
            if len(attempts) == 1:
                raise httpx.ConnectTimeout("cold worker", request=request)
            if len(attempts) == 2:
                return httpx.Response(503)
        return fake(request)

    transport(monkeypatch, flaky)
    assert encoder.RunPodEncoder("endpoint", "test-key").encode(["public text"]) == [VECTOR]
    assert len(attempts) == 3 and len(fake.submitted) == 1


def test_submit_gives_up_after_bounded_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def down(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        raise httpx.ConnectError("unreachable", request=request)

    transport(monkeypatch, down)
    monkeypatch.setattr(encoder, "SUBMIT_BACKOFF_S", 0)
    with pytest.raises(httpx.ConnectError):
        encoder.RunPodEncoder("endpoint", "test-key").encode(["public text"])
    assert calls == ["/v2/endpoint/run"] * encoder.SUBMIT_ATTEMPTS  # never cancels: no job id


def test_submit_read_timeout_is_never_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """The POST may have been accepted; a retry could start a second paid job."""
    calls = []

    def slow(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        raise httpx.ReadTimeout("accepted?", request=request)

    transport(monkeypatch, slow)
    with pytest.raises(httpx.ReadTimeout):
        encoder.RunPodEncoder("endpoint", "test-key").encode(["public text"])
    assert calls == ["/v2/endpoint/run"]


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED", "TIMED_OUT"])
def test_failed_job_is_not_a_valid_snapshot_input(monkeypatch, status: str) -> None:
    fake = FakeRunPod(statuses=[{"status": status}])
    transport(monkeypatch, fake)
    with pytest.raises(RuntimeError):
        encoder.RunPodEncoder("endpoint", "test-key").encode(["public sentence"])
    assert fake.paths[-1] == "/v2/endpoint/cancel/job-1"


def test_deadline_exceeded_cancels_the_known_job(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    fake = FakeRunPod(statuses=[{"status": "IN_QUEUE"}] * 1000)
    transport(monkeypatch, fake)
    monkeypatch.setattr(encoder.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(encoder.time, "sleep", lambda s: clock.__setitem__(0, clock[0] + s))
    with pytest.raises(TimeoutError):
        encoder.RunPodEncoder("endpoint", "test-key", timeout=30).encode(["public text"])
    assert fake.paths[-1] == "/v2/endpoint/cancel/job-1"
    assert clock[0] <= 30


def test_unknown_model_revision_is_rejected(monkeypatch) -> None:
    value = completed()
    value["output"]["revision"] = "different-weights"
    fake = FakeRunPod(statuses=[value])
    transport(monkeypatch, fake)
    with pytest.raises(ValueError, match="incompatible"):
        encoder.RunPodEncoder("endpoint", "test-key").encode(["public sentence"])


def test_wrong_vector_count_is_rejected(monkeypatch) -> None:
    fake = FakeRunPod(statuses=[completed(2)])
    transport(monkeypatch, fake)
    with pytest.raises(ValueError, match="wrong number"):
        encoder.RunPodEncoder("endpoint", "test-key").encode(["public sentence"])


def test_timeout_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRENDS_RUNPOD_TIMEOUT_SECONDS", raising=False)
    assert encoder.configured_timeout() == 600
    monkeypatch.setenv("TRENDS_RUNPOD_TIMEOUT_SECONDS", "240")
    assert encoder.configured_timeout() == 240
    for bad in ("0", "901", "nan"):
        monkeypatch.setenv("TRENDS_RUNPOD_TIMEOUT_SECONDS", bad)
        with pytest.raises(ValueError):
            encoder.configured_timeout()


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
