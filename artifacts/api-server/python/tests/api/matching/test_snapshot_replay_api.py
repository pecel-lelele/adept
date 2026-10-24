"""A requested M1 snapshot date drives both matching endpoints."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.features.trends import mocks as trends_mocks


def test_matching_replays_requested_snapshot(client: TestClient) -> None:
    older, latest = trends_mocks.AVAILABLE_MOCK_DATES[0], trends_mocks.AVAILABLE_MOCK_DATES[-1]
    responses = [
        client.get("/api/v1/matches", params={"scenario": "moderate", "snapshot_date": day})
        for day in (older, latest)
    ]

    assert all(response.status_code == 200 for response in responses)
    for day, response in zip((older, latest), responses, strict=True):
        body = response.json()
        assert body["meta"]["snapshot_date"] == day.isoformat()
        assert (
            body["data_provenance_note"]
            == trends_mocks.snapshot("moderate", day).meta.data_provenance_note
        )
        assert all(match["meta"]["snapshot_date"] == day.isoformat() for match in body["matches"])
        assert all(
            match["data_provenance_note"] == body["data_provenance_note"]
            for match in body["matches"]
        )

    role_id = responses[0].json()["matches"][0]["role_id"]
    detail = client.get(
        f"/api/v1/matches/{role_id}",
        params={"scenario": "moderate", "snapshot_date": older},
    )
    assert detail.status_code == 200
    assert detail.json()["meta"]["snapshot_date"] == older.isoformat()
    assert (
        detail.json()["data_provenance_note"]
        == trends_mocks.snapshot("moderate", older).meta.data_provenance_note
    )


def test_matching_rejects_unknown_snapshot_date(client: TestClient) -> None:
    response = client.get(
        "/api/v1/matches",
        params={"scenario": "moderate", "snapshot_date": date(2000, 1, 1)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
