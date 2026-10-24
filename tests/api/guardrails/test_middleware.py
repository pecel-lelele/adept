from collections.abc import Iterator

from fastapi.testclient import TestClient


def test_security_headers_on_api_responses(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]


def test_docs_keep_working_without_strict_csp(client: TestClient) -> None:
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "Content-Security-Policy" not in resp.headers


def test_rate_limit_headers_present(client: TestClient) -> None:
    assert "X-RateLimit-Limit" in client.get("/api/v1/health").headers


def test_declared_oversized_json_body_is_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/profile",
        content=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": str(50 * 1024 * 1024)},
    )
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "payload_too_large"


def _chunks(total: int, size: int = 64 * 1024) -> Iterator[bytes]:
    sent = 0
    while sent < total:
        n = min(size, total - sent)
        sent += n
        yield b"x" * n


def test_chunked_json_body_without_length_is_cut_off(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/profile",
        content=_chunks(3 * 1024 * 1024),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "payload_too_large"


def test_chunked_cv_upload_is_cut_off_before_parsing(client: TestClient) -> None:
    boundary = "adeptboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="cv.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
    ).encode()

    def body() -> Iterator[bytes]:
        yield head
        yield from _chunks(7 * 1024 * 1024)
        yield f"\r\n--{boundary}--\r\n".encode()

    resp = client.post(
        "/api/v1/profile/cv",
        content=body(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    assert resp.status_code == 413


def test_small_chunked_body_still_works(client: TestClient) -> None:
    payload = b'{"segment":"working","interests":[],"hours_per_week":5,"budget_myr":0,'
    payload += b'"hrd_eligible":false}'
    resp = client.post(
        "/api/v1/profile",
        content=iter([payload[:20], payload[20:]]),
        headers={"Content-Type": "application/json", "X-Demo-User": "ravi"},
    )
    assert resp.status_code == 200
