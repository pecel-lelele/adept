"""Synthetic PDF limits for direct extraction and the public preview endpoint."""

import multiprocessing

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.features.profile import cv_parser


def _pdf(pages: int) -> bytes:
    with pymupdf.open() as document:
        for _ in range(pages):
            document.new_page().insert_text((72, 72), "Synthetic CV")
        return document.tobytes()


def test_rejects_500_pages_before_extracting_text() -> None:
    with pytest.raises(AppError) as error:
        cv_parser.extract_text(_pdf(500), "application/pdf")
    assert error.value.code == "pdf_too_many_pages"
    assert error.value.status_code == 422


def test_normal_pdf_still_extracts() -> None:
    assert "Synthetic CV" in cv_parser.extract_text(_pdf(1), "application/pdf")


@pytest.mark.parametrize("pages, status", [(500, 422), (1, 200)])
def test_public_preview_enforces_pdf_limits(client: TestClient, pages: int, status: int) -> None:
    response = client.post(
        "/api/v1/preview/cv?include_suggestions=false",
        data={"synthetic_consent": "true"},
        files={"file": ("synthetic.pdf", _pdf(pages), "application/pdf")},
    )
    assert response.status_code == status
    if status == 422:
        assert response.json()["error"]["code"] == "pdf_too_many_pages"


def test_timeout_reaps_the_parser_process(monkeypatch: pytest.MonkeyPatch) -> None:
    previous = {process.pid for process in multiprocessing.active_children()}
    monkeypatch.setattr(cv_parser, "PDF_PARSE_TIMEOUT_S", 0.001)
    with pytest.raises(AppError) as error:
        cv_parser.extract_pdf_bounded(_pdf(1))
    assert error.value.code == "pdf_timeout"
    assert {process.pid for process in multiprocessing.active_children()} == previous


def test_busy_parser_does_not_queue_work() -> None:
    slots = cv_parser._PDF_PARSE_SLOTS
    acquired = []
    try:
        while slots.acquire(blocking=False):
            acquired.append(True)
        with pytest.raises(AppError) as error:
            cv_parser.extract_pdf_bounded(_pdf(1))
        assert error.value.code == "pdf_busy"
        assert error.value.status_code == 503
    finally:
        for _ in acquired:
            slots.release()
