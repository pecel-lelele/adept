"""Data access for profiles. In-memory copy of mocks; later `profiles` + `user_skills`."""

from app.contracts.profile import Profile
from app.features.profile import mocks

_store: dict[str, Profile] = {uid: p.model_copy(deep=True) for uid, p in mocks.PROFILES.items()}


def get_profile(user_id: str) -> Profile | None:
    return _store.get(user_id)


def save_profile(profile: Profile) -> Profile:
    _store[profile.user_id] = profile
    return profile
