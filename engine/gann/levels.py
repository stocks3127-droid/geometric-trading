"""Support & resistance levels — Rulebook Part 1, Module 08 (Rules 82–94).

Rule 82 is the king: divide the range by 2, 3, 4, 6, 8, 12, 16 — the 50%
midpoint is always the strongest level.
"""

from __future__ import annotations

from typing import Iterable

__all__ = ["range_levels", "ath_levels", "atl_multiples", "nearest", "confluence"]


# Rule 82 (and Rule 42 range-division lines).
RANGE_FRACTIONS: tuple[float, ...] = (
    1 / 12, 1 / 8, 1 / 6, 1 / 4, 1 / 3,
    1 / 2,                        # <- king
    2 / 3, 3 / 4, 5 / 6, 7 / 8, 11 / 12,
)

_LABELS = {
    1 / 12: "1/12", 1 / 8: "1/8", 1 / 6: "1/6", 1 / 4: "1/4", 1 / 3: "1/3",
    1 / 2: "1/2 (KING)", 2 / 3: "2/3", 3 / 4: "3/4", 5 / 6: "5/6", 7 / 8: "7/8",
    11 / 12: "11/12",
}


def range_levels(high: float, low: float) -> dict[str, float]:
    """Range-division S/R levels, Rule 82.  Ordered from low to high."""
    rng = high - low
    if rng < 0:
        raise ValueError("high must be >= low")
    out = {(_LABELS[f]): low + f * rng for f in RANGE_FRACTIONS}
    return dict(sorted(out.items(), key=lambda kv: kv[1]))


def ath_levels(all_time_high: float) -> dict[str, float]:
    """Rule 86: divide the all-time high by 2 and by 3 for major S/R."""
    return {"ATH/3": all_time_high / 3.0, "ATH/2": all_time_high / 2.0}


def atl_multiples(all_time_low: float) -> dict[str, float]:
    """Rule 87: multiply the all-time low by 2, 3, 4 for S/R levels."""
    return {f"ATL x{k}": all_time_low * k for k in (2, 3, 4)}


def nearest(price: float, levels: dict[str, float], k: int = 6) -> list[tuple[str, float, float]]:
    """Nearest levels to ``price``: ``(label, level, distance)`` closest first."""
    ranked = sorted(levels.items(), key=lambda kv: abs(kv[1] - price))
    return [(lbl, lvl, lvl - price) for lbl, lvl in ranked[:k]]


def confluence(*level_dicts: dict[str, float], tol_pct: float = 0.15) -> list[tuple[float, list[str]]]:
    """Merge level dicts and cluster levels within ``tol_pct``% of each other.

    Confluence of a range division with a Square-of-9 level is the classic
    Gann confirmation (Part 1 M08 + Part 2 M13 used together).
    """
    items: list[tuple[str, float]] = []
    for d in level_dicts:
        items.extend(d.items())
    items.sort(key=lambda t: t[1])
    clusters: list[tuple[float, list[str]]] = []
    for lbl, lvl in items:
        if clusters and abs(lvl - clusters[-1][0]) / max(clusters[-1][0], 1e-9) * 100 <= tol_pct:
            clusters[-1][1].append(lbl)
        else:
            clusters.append((lvl, [lbl]))
    return clusters
