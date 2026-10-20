"""API security layer (F8, owner M3). Patterns adapted from KerjaCerdas; see each module.

`install_security(app)` is called once from `app.main.create_app`, before CORS is added,
so CORS stays outermost and error responses from these middlewares still carry CORS headers.
Execution order (outer → inner): CORS → security headers → rate limit → body size → route.
"""

from fastapi import FastAPI

from app.core.config import Settings
from app.core.security.body_limit import BodySizeLimitMiddleware
from app.core.security.headers import SecurityHeadersMiddleware
from app.core.security.pii import contains_pii, redact_text
from app.core.security.rate_limit import RateLimitMiddleware
from app.core.security.sanitize import (
    SanitizedStr,
    clean_extracted_text,
    find_injection,
    sanitize_filename,
    sanitize_text,
)


def install_security(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        BodySizeLimitMiddleware,
        max_json_bytes=settings.max_json_bytes,
        max_upload_bytes=settings.max_upload_bytes,
    )
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            default=(settings.rate_limit_default, settings.rate_limit_window_s),
            proxy_secret=settings.proxy_shared_secret,
            # One limit across all API instances when state lives in PostgreSQL.
            shared_conninfo=settings.database_url if settings.m3_backend == "postgres" else "",
        )
    app.add_middleware(SecurityHeadersMiddleware)


__all__ = [
    "SanitizedStr",
    "clean_extracted_text",
    "contains_pii",
    "find_injection",
    "install_security",
    "redact_text",
    "sanitize_filename",
    "sanitize_text",
]
