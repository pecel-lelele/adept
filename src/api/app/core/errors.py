"""Shared error types, rendered as {"error": {"code", "message"}}."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


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
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=401, code="unauthorized")


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


def register_error_handlers(app: FastAPI) -> None:
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
