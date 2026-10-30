"""RunPod cleanup and whole-encode deadline checks using an in-memory transport."""

import json

import httpx
import pytest

from pipelines.trends import encoder


def _completed() -> dict[str, object]:
    return {
        "id": "job-test",
        "status": "COMPLETED",
        "output": {
            "model": encoder.MODEL_ID,
            "revision": encoder.MODEL_REVISION,
            "dimensions": encoder.DIMENSIONS,
            "embeddings": [[1.0] + [0.0] * 383],
        },
    }


@pytest.mark.parametrize("outcome", ["timeout", "exception", "cancel-failure", "success"])
def test_cancel_unfinished_jobs_only(monkeypatch: pytest.MonkeyPatch, outcome: str) -> None:
    paths: list[str] = []
    clock = [0.0]

    def response(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if "/cancel/" in request.url.path:
            if outcome == "cancel-failure":
                return httpx.Response(503)
            return httpx.Response(200, json={"status": "CANCELLED"})
        if request.url.path.endswith("/run"):
            return httpx.Response(200, json={"id": "job-test", "status": "IN_PROGRESS"})
        if outcome in {"exception", "cancel-failure"}:
            return httpx.Response(400)  # non-transient: fails at once
        return httpx.Response(
            200, json=_completed() if outcome == "success" else {"status": "IN_PROGRESS"}
        )

    client = httpx.Client
    monkeypatch.setattr(
        encoder.httpx, "Client", lambda **kw: client(transport=httpx.MockTransport(response), **kw)
    )
    monkeypatch.setattr(encoder.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        encoder.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )
    subject = encoder.RunPodEncoder("synthetic", "synthetic-key", timeout=2)
    if outcome == "success":
        assert len(subject.encode(["public synthetic text"])) == 1
    else:
        with pytest.raises(
            TimeoutError if outcome == "timeout" else httpx.HTTPStatusError
        ) as error:
            subject.encode(["public synthetic text"])
        if outcome == "cancel-failure":
            assert any("cancellation failed" in note for note in error.value.__notes__)
    assert ("/v2/synthetic/cancel/job-test" in paths) == (outcome != "success")


def test_encode_has_one_deadline_across_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    policies: list[object] = []
    timeouts: list[float] = []

    def response(request: httpx.Request) -> httpx.Response:
        policies.append(json.loads(request.content).get("policy"))
        timeouts.append(request.extensions["timeout"]["read"])
        clock[0] += 3
        return httpx.Response(200, json=_completed())

    client = httpx.Client
    monkeypatch.setattr(
        encoder.httpx, "Client", lambda **kw: client(transport=httpx.MockTransport(response), **kw)
    )
    monkeypatch.setattr(encoder.time, "monotonic", lambda: clock[0])
    with pytest.raises(TimeoutError):
        encoder.RunPodEncoder("synthetic", "synthetic-key", timeout=5).encode(
            ["one", "two", "three"], batch_size=1
        )
    assert len(policies) == 2
    assert policies == [{"executionTimeout": 5000, "ttl": 10000}] * 2
    assert timeouts == [5, 2]
