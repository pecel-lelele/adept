"""Security headers on every Adept API response."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Swagger UI and ReDoc load scripts and styles, so they get no CSP from us.
_DOC_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("X-Frame-Options", "DENY")
        if not request.url.path.startswith(_DOC_PATHS):
            h.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            h.setdefault("Cache-Control", "no-store")
        return response
