"""JWT verification for AUTH_MODE=supabase. Pattern from KerjaCerdas `auth_service.py`.

Supabase signs access tokens with the project's JWT secret (HS256) and sets
`aud = "authenticated"`. We fail closed: no secret configured → no access.

Privilege comes only from `app_metadata` (writable by the server only). `user_metadata` is
editable by the user, so it is used for the display name and never for the account kind.
"""

from __future__ import annotations

from typing import Any

import jwt

from app.core.errors import AppError, UnauthorizedError

ALGORITHMS = ["HS256"]


def bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise UnauthorizedError("Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthorizedError("Authorization header must be 'Bearer <token>'")
    return token.strip()


def decode_token(token: str, secret: str, audience: str) -> dict[str, Any]:
    if not secret:
        raise AppError(
            "SUPABASE_JWT_SECRET is not configured", status_code=503, code="auth_unconfigured"
        )
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            secret,
            algorithms=ALGORITHMS,
            audience=audience,
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid token") from exc
    return claims
