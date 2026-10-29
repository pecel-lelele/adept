"""Shared error types, rendered as {"error": {"code", "message"}}."""

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

log = get_logger("app.errors")


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "bad_request") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404, code="not_found")


class UnauthorizedError(AppError):
    def __init__(self, message: str, code: str = "unauthorized") -> None:
        super().__init__(message, status_code=401, code=code)


class ForbiddenError(AppError):
    def __init__(self, message: str, code: str = "forbidden") -> None:
        super().__init__(message, status_code=403, code=code)


class ProfileRequiredError(AppError):
    """Raised when a user without a saved profile attempts to compute matches.

    Maps to HTTP 400 Bad Request.
    """

    def __init__(
        self,
        message: str = "Profile required: please complete your skills profile first.",
    ) -> None:
        super().__init__(message, status_code=400, code="profile_required")


class PdfSupportUnavailable(AppError):
    """Raised when fitz (PyMuPDF) is not installed and a PDF is uploaded.

    Maps to HTTP 501 Not Implemented.
    """

    def __init__(
        self,
        message: str = (
            "PDF parsing is not available on this server. Install PyMuPDF (pymupdf) to enable it."
        ),
    ) -> None:
        super().__init__(message, status_code=501, code="pdf_unsupported")


class PdfNoText(AppError):
    """Raised when a PDF is uploaded but yields no extractable text (e.g. scanned image).

    Maps to HTTP 422 Unprocessable Entity.
    """

    def __init__(
        self,
        message: str = (
            "The uploaded PDF contains no extractable text "
            "(it may be a scanned image). Please paste the text instead."
        ),
    ) -> None:
        super().__init__(message, status_code=422, code="pdf_no_text")


class TrendUnavailableError(Exception):
    """Raised when the trend snapshot service cannot be reached or returns no data.

    Maps to HTTP 503 Service Unavailable.  Never swallowed silently.
    """

    code = "trend_unavailable"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _validation_message(exc: RequestValidationError) -> str:
    """One readable line, e.g. "query.role_id: Field required; body.level: ..."."""
    parts: list[str] = []
    for err in exc.errors()[:5]:
        loc = ".".join(str(p) for p in err.get("loc", ()) if p != "body") or "request"
        parts.append(f"{loc}: {err.get('msg', 'invalid value')}")
    return "; ".join(parts) or "Invalid request"


def register_error_handlers(app: FastAPI) -> None:
    """Every error leaves the API as {"error": {"code", "message"}} so the web client can
    show one consistent message (validation, unknown routes and database outages included)."""

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": _validation_message(exc)}},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {404: "not_found", 405: "method_not_allowed", 401: "unauthorized"}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": codes.get(exc.status_code, "http_error"),
                    "message": str(exc.detail),
                }
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(psycopg.OperationalError)
    async def _handle_db_down(_: Request, exc: psycopg.OperationalError) -> JSONResponse:
        log.warning("database unavailable: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "storage_unavailable",
                    "message": "The database is unavailable right now. Please try again shortly.",
                }
            },
        )

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(TrendUnavailableError)
    async def _handle_trend_unavailable(_: Request, exc: TrendUnavailableError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
