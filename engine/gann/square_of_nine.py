"""Square of 9 (and Square of 4) — Rulebook Part 2, Module 11 (Rules 130–139)
plus Square of 9 fixed-table rules from Part 1, Module 10 (Rule 115).

The engine of the Square of 9 is the classic square-root rotation:

    price at d degrees from center  =  (sqrt(center) ± d/180) ** 2

A full 360-degree revolution adds **2** to the square root; each 90 degrees
adds 0.5, each 45 degrees adds 0.25.

Rule 134 worked example (verified against this formula):
    center 496 -> 45° up = 507, 90° up = 518, 180° up = 541,
                  45° dn = 485, 90° dn = 474, 180° dn = 452.

Note: the rulebook's "120°" figures (529 / 463) correspond to 135° in the
standard formula (sqrt delta 0.75); both 120° and 135° are included in the
default step list so you can watch either convention.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

__all__ = [
    "DEFAULT_STEPS",
    "price_at_degree",
    "levels_around",
    "degrees_position",
    "price_aspecting",
    "circle_ends",
    "cardinal_cross",
    "diagonal_cross",
    "ring_of",
]


# Rule 135 / Rule 138 degree steps, with Rule 138 importance ranks.
# rank 1 = highest probability trend-change (90 days/degrees), etc.
DEFAULT_STEPS: tuple[int, ...] = (45, 90, 120, 135, 144, 180, 216, 225, 270, 315, 360)

CYCLE_RANKS: dict[int, int] = {
    90: 1, 45: 2, 180: 3, 135: 4, 270: 5,
    120: 6, 315: 7, 225: 8, 144: 9, 216: 10,
}


# ---------------------------------------------------------------------------
# Core rotation math
# ---------------------------------------------------------------------------

def price_at_degree(center: float, degrees: float, up: bool = True) -> float:
    """Price after rotating ``degrees`` around the wheel from ``center``.

    ``up=True`` walks the spiral outward (resistance above);
    ``up=False`` walks inward (support below).
    """
    if center <= 0:
        raise ValueError("center price must be > 0")
    root = math.sqrt(center) + (degrees / 180.0 if up else -degrees / 180.0)
    if root < 0:
        raise ValueError(f"{degrees}° below {center} wraps below zero")
    return root * root


def levels_around(
    center: float,
    price: float | None = None,
    steps: Sequence[float] = DEFAULT_STEPS,
) -> dict[str, list[tuple[float, float]]]:
    """Resistance above and support below ``price`` on the wheel.

    Returns ``{"resistance": [(degrees, level), ...], "support": [...]}``
    sorted by distance from ``price`` (closest first).  Default ``price``
    is the center itself (Rule 134: set center = contract low, then read
    resistance prices above it).
    """
    ref = center if price is None else price
    res, sup = [], []
    for d in steps:
        try:
            r = price_at_degree(center, d, up=True)
            if r > ref:
                res.append((float(d), r))
        except ValueError:
            pass
        try:
            s = price_at_degree(center, d, up=False)
            if s < ref and s > 0:
                sup.append((float(d), s))
        except ValueError:
            pass
    res.sort(key=lambda t: abs(t[1] - ref))
    sup.sort(key=lambda t: abs(t[1] - ref))
    return {"resistance": res, "support": sup}


def degrees_position(price: float, center: float) -> float:
    """Signed degrees of ``price`` around the wheel measured from ``center``.

    Positive = rotated outward (above center), negative = inward.
    Used for Rule 136 *price aspecting*: when the date's angle on the wheel
    equals the price's angle, time is aspecting price — a natural
    resistance / high-probability reversal point.
    """
    return (math.sqrt(price) - math.sqrt(center)) * 180.0


def price_aspecting(price: float, center: float, date_degrees: float, tolerance: float = 2.0) -> bool:
    """Rule 136: is the date aspecting the price on the wheel?"""
    return abs(((degrees_position(price, center) - date_degrees) + 180.0) % 360.0 - 180.0) <= tolerance


# ---------------------------------------------------------------------------
# Fixed table geometry (Rules 130–133)
# ---------------------------------------------------------------------------

def circle_ends(kind: str = "sq9", n: int = 10) -> list[int]:
    """Circle-completion numbers.

    Rule 130 — Square of 9 ends at squares of odd numbers: 9, 25, 49, 81, ...
    Rule 131 — Square of 4 ends at squares of even numbers: 4, 16, 36, 64, ...
    """
    if kind == "sq9":
        return [(2 * k + 1) ** 2 for k in range(1, n + 1)]
    if kind == "sq4":
        return [(2 * k) ** 2 for k in range(1, n + 1)]
    raise ValueError("kind must be 'sq9' or 'sq4'")


def _cross_number(ring: int, arm: str) -> int:
    """Closed-form number on the cardinal / diagonal cross for ``ring`` n.

    Conventions (match Rule 132/133 sequences):
      N (vertical up)   4n² − n + 1     -> 4, 15, 34, 61, 96, 139, ...
      E (horizontal r)  4n² + n + 1     -> 6, 19, 40, 69, 106, 151, ...
      S (vertical down) 4n² + 3n + 1    -> 8, 23, 46, 77, 116, 163, ...
      W (horizontal l)  4n² − 3n + 1    -> 2, 11, 28, 53, 86, 127, ...
      NE diagonal       4n² + 2n + 1?   -> see diagonal_cross()
    """
    n = ring
    return {
        "N": 4 * n * n - n + 1,
        "E": 4 * n * n + n + 1,
        "S": 4 * n * n + 3 * n + 1,
        "W": 4 * n * n - 3 * n + 1,
    }[arm]


def cardinal_cross(rings: int = 10) -> dict[str, list[int]]:
    """Numbers on the vertical/horizontal arms through the center (Rule 132).

    Primary resistance on the Square of 9.  (The rulebook's vertical-up
    sequence lists 129 at ring 6; the closed form and every neighbouring
    term give 139 — treated there as a typo.)
    """
    return {arm: [_cross_number(n, arm) for n in range(1, rings + 1)] for arm in ("N", "E", "S", "W")}


def diagonal_cross(rings: int = 10) -> dict[str, list[int]]:
    """Numbers on the two X diagonals from the center (Rule 133).

    Secondary resistance: NW arm 3, 13, 31, 57, 91, ... and SE arm
    7, 21, 43, 73, 111, ...
    """
    return {
        "NW": [4 * n * n - 2 * n + 1 for n in range(1, rings + 1)],
        "SE": [4 * n * n + 2 * n + 1 for n in range(1, rings + 1)],
    }


def ring_of(number: int) -> int:
    """Which ring of the Square of 9 a number sits on.

    Ring n spans ((2n−1)², (2n+1)²]; ring 0 is just the center 1.
    e.g. 9 -> ring 1, 10 -> ring 2, 25 -> ring 2, 26 -> ring 3.
    """
    if number <= 1:
        return 0
    return math.ceil((math.sqrt(number) - 1.0) / 2.0)


def nearest_wheel_levels(
    center: float,
    price: float,
    steps: Iterable[float] = DEFAULT_STEPS,
    k: int = 5,
) -> dict[str, list[tuple[float, float]]]:
    """Top-k nearest resistance/support wheel levels around ``price``."""
    lv = levels_around(center, price, list(steps))
    return {"resistance": lv["resistance"][:k], "support": lv["support"][:k]}
