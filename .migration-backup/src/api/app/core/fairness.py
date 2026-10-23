"""Fairness guards (F8, owner M3; used by F4, F5, F7).

Two layers, both enforced in CI:

1. **Input exclusion**: no API input (request body or query parameter) and no database column
   may carry a protected attribute. `protected_terms_in` finds offending field names.
2. **Counterfactual invariance**: a recommendation function must return the same result when
   only identity changes. `counterfactual_diffs` runs the function over variants and reports
   any that differ from the baseline.

Protected attributes follow Malaysia's Federal Constitution Art. 8 grounds and SDG target
10.2 ("irrespective of age, sex, disability, race, ethnicity, origin, religion or economic or
other status"). Names are included because names act as a proxy for gender and ethnicity.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeVar

PROTECTED_TERMS: tuple[str, ...] = (
    "age",
    "birth",
    "dob",
    "gender",
    "sex",
    "race",
    "ethnic",
    "religion",
    "nationality",
    "citizenship",
    "marital",
    "disability",
    "pregnan",
    "photo",
    "full_name",
    "first_name",
    "last_name",
)

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(field_name: str) -> list[str]:
    return _WORD.findall(field_name.lower().replace("-", "_"))


def is_protected(field_name: str) -> bool:
    """True if a field name refers to a protected attribute.

    Matches whole tokens (so `age` flags `age` and `user_age` but not `page` or `usage`),
    prefixes for stems such as `ethnic`/`pregnan`, and multi-word names such as `full_name`.
    """
    name = field_name.lower().replace("-", "_")
    tokens = _tokens(name)
    for term in PROTECTED_TERMS:
        if "_" in term:
            if term in name:
                return True
        elif any(tok == term or (len(term) > 4 and tok.startswith(term)) for tok in tokens):
            return True
    return False


def protected_terms_in(field_names: Iterable[str]) -> list[str]:
    return sorted({f for f in field_names if is_protected(f)})


T = TypeVar("T")


def counterfactual_diffs(
    fn: Callable[[Any], T],
    baseline: Any,
    variants: Mapping[str, Any],
    key: Callable[[T], object] = lambda r: r,
) -> list[str]:
    """Names of variants whose result differs from the baseline's (empty = invariant)."""
    expected = key(fn(baseline))
    return [name for name, variant in variants.items() if key(fn(variant)) != expected]
