"""Signed session tokens and password hashing for local accounts (Core, M4).

The web server keeps the token in an httpOnly cookie and forwards it to the API, so a browser
can never pick another user's id: the API only accepts ids it signed itself.

Passwords are hashed with scrypt (stdlib, memory-hard). Only the hash is stored.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time

from app.core.config import REPO_ROOT, get_settings

logger = logging.getLogger(__name__)

TOKEN_PREFIX = "v1"
SESSION_TTL_S = 14 * 24 * 3600
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


# Local fallback key when SESSION_SECRET is unset: random, never derived from public values.
SECRET_FILE = REPO_ROOT / ".session-secret"
_fallback: bytes | None = None


def _local_secret() -> bytes:
    """A random key kept in a gitignored file so local restarts keep sessions.

    If the file can't be written (read-only container), the key lives in memory only and
    sessions end when the process restarts. Deployments set SESSION_SECRET instead.
    """
    global _fallback
    if _fallback is not None:
        return _fallback
    try:
        stored = SECRET_FILE.read_text(encoding="ascii").strip()
        if len(stored) >= 64:
            _fallback = bytes.fromhex(stored)
            return _fallback
    except (OSError, ValueError):
        pass
    key = secrets.token_bytes(32)
    try:
        SECRET_FILE.write_text(key.hex(), encoding="ascii")
        os.chmod(SECRET_FILE, 0o600)
    except OSError:
        logger.warning("SESSION_SECRET is not set: using an in-memory key for this process")
    _fallback = key
    return key


def _secret() -> bytes:
    settings = get_settings()
    if settings.session_secret:
        return settings.session_secret.encode()
    return _local_secret()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    return _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())


def issue(user_id: str, now: float | None = None) -> str:
    expires = int((now if now is not None else time.time()) + SESSION_TTL_S)
    payload = f"{TOKEN_PREFIX}.{_b64(user_id.encode())}.{expires}"
    return f"{payload}.{_sign(payload)}"


def verify(token: str, now: float | None = None) -> str | None:
    """Return the user id of a valid, unexpired token, else None."""
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != TOKEN_PREFIX:
        return None
    payload = ".".join(parts[:3])
    if not hmac.compare_digest(_sign(payload), parts[3]):
        return None
    try:
        expires = int(parts[2])
        user_id = _unb64(parts[1]).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    if expires < (now if now is not None else time.time()):
        return None
    return user_id or None


def looks_like_token(value: str) -> bool:
    return value.startswith(TOKEN_PREFIX + ".")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str | None) -> bool:
    if not stored or not stored.startswith("scrypt$"):
        return False
    try:
        _, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)
