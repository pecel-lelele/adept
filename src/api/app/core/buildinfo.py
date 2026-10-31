"""Public build identity, without exposing environment variables or credentials."""

import os
import re

from app.core.config import REPO_ROOT


def revision() -> str | None:
    value = os.environ.get("BUILD_REVISION", "").strip()
    if not value:
        try:
            value = (REPO_ROOT / "src/web/.next/adept-revision.txt").read_text().strip()
        except OSError:
            return None
    return value if re.fullmatch(r"[0-9a-f]{40}", value) else None


def dirty() -> bool | None:
    try:
        value = (REPO_ROOT / "src/web/.next/adept-dirty.txt").read_text().strip()
    except OSError:
        return None
    return {"true": True, "false": False}.get(value)
