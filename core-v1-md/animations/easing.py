"""Easing curves mapping t∈[0,1] → [0,1]."""

from __future__ import annotations

import math
from collections.abc import Callable

Easing = Callable[[float], float]


def linear(t: float) -> float:
    return t


def in_cubic(t: float) -> float:
    return t * t * t


def out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def in_out_cubic(t: float) -> float:
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2


def out_expo(t: float) -> float:
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def steps(n: int) -> Easing:
    """Quantised easing – gives a mechanical, segment-display feel."""
    return lambda t: min(1.0, math.floor(t * n) / n) if t < 1 else 1.0


EASINGS: dict[str, Easing] = {
    "linear": linear,
    "in_cubic": in_cubic,
    "out_cubic": out_cubic,
    "in_out_cubic": in_out_cubic,
    "in_out_sine": in_out_sine,
    "out_expo": out_expo,
    "steps8": steps(8),
}


def get_easing(name: str | None) -> Easing:
    if not name:
        return out_cubic
    try:
        return EASINGS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown easing {name!r}; available: {sorted(EASINGS)}") from exc
