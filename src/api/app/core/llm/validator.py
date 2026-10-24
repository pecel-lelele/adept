"""ID validation: reject anything the model invents."""

from collections.abc import Collection, Iterable


class UnknownIdError(ValueError):
    def __init__(self, unknown: list[str]) -> None:
        super().__init__(f"LLM returned unknown IDs: {', '.join(unknown)}")
        self.unknown = unknown


def validate_ids(selected: Iterable[str], allowed: Collection[str]) -> list[str]:
    """Return the selected IDs (deduplicated, in order) or raise if any is unknown."""
    seen: dict[str, None] = {}
    for item in selected:
        seen.setdefault(item, None)
    unknown = [i for i in seen if i not in allowed]
    if unknown:
        raise UnknownIdError(unknown)
    return list(seen)
