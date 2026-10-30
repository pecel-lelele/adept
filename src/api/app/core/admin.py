"""Operator-assigned administrators, independent of unverified email addresses."""

from app.core import accounts
from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.errors import ForbiddenError


def require_admin(user: CurrentUser) -> CurrentUser:
    allowed = {value.strip() for value in get_settings().admin_user_ids.split(",") if value.strip()}
    if user.id not in allowed or accounts.find_by_id(user.id) is None:
        raise ForbiddenError("Only configured administrators can manage trend data.")
    return user
