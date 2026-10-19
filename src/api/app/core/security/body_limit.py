"""Reject oversized request bodies before they are parsed. Adapted from KerjaCerdas.

This checks the declared Content-Length only. Uploads without one (chunked) are still
bounded by the capped read in the CV route (`features/profile/router.py:read_capped`).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

# Multipart overhead (boundaries, part headers) on top of the file itself.
_MULTIPART_SLACK = 64 * 1024


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_json_bytes: int, max_upload_bytes: int) -> None:
        super().__init__(app)
        self.max_json_bytes = max_json_bytes
        self.max_upload_bytes = max_upload_bytes + _MULTIPART_SLACK

    def limit_for(self, content_type: str) -> int:
        if content_type.startswith("multipart/form-data"):
            return self.max_upload_bytes
        return self.max_json_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        declared = request.headers.get("content-length")
        if declared is not None:
            if not declared.isdigit():
                return _error(400, "bad_request", "Invalid Content-Length header.")
            if int(declared) > self.limit_for(request.headers.get("content-type", "")):
                return _error(413, "payload_too_large", "Request payload too large.")
        return await call_next(request)
