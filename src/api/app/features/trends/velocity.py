"""Serving-time velocity bound shared by every snapshot source (F2).

The trend pipeline clamps both scenario velocities to +/-2 (`pipelines/trends/score.py`), but
older stored snapshots and the bundled mock fixtures were written before Moderate was clamped.
Applying the same bound where items are built keeps Fast >= Moderate for rising skills on every
served snapshot.

The API runtime does not ship the offline `pipelines` package, so the bound is defined here;
`tests/api/trends/test_served_velocity_clamp.py` pins it to the pipeline's constants.
"""

from __future__ import annotations

V_CLAMP_MIN = -2.0
V_CLAMP_MAX = 2.0


def served_velocity(value: float) -> float:
    return max(V_CLAMP_MIN, min(V_CLAMP_MAX, float(value)))
