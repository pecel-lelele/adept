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
