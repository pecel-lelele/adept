import pytest
from fastapi.testclient import TestClient

from app.contracts.guardrails import Disclosure, FairnessReport, SourcesResponse
from app.core.config import get_settings


def test_disclosure_reflects_configuration(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = Disclosure.model_validate(client.get("/api/v1/guardrails/disclosure").json())
    assert body.provider == "none" and not body.llm_enabled and body.model == ""
    assert any("catalogue" in rule for rule in body.rules)
    monkeypatch.setattr(get_settings(), "llm_provider", "example-provider")
    monkeypatch.setattr(get_settings(), "llm_model", "example-model-1")
    body = Disclosure.model_validate(client.get("/api/v1/guardrails/disclosure").json())
    assert (body.provider, body.model, body.llm_enabled) == (
        "example-provider",
        "example-model-1",
        True,
    )


def test_source_register_lists_dated_sources(client: TestClient) -> None:
    body = SourcesResponse.model_validate(client.get("/api/v1/guardrails/sources").json())
    names = {s.name for s in body.sources}
    assert {"UN Statistics Division SDG API", "Microsoft Learn Catalog API"} <= names
    assert all(s.retrieved_at and s.records >= 0 for s in body.sources)
    assert {s.kind for s in body.sources} >= {"live_api", "verified_page", "synthetic"}


def test_fairness_report_passes(client: TestClient) -> None:
    body = FairnessReport.model_validate(client.get("/api/v1/guardrails/fairness").json())
    assert body.passed and body.protected_inputs_found == [] and body.api_inputs_checked > 0
