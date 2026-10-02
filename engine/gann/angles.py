"""Gann geometric angles — Rulebook Part 1, Module 04 (Rules 24–42).

A Gann angle's slope is expressed in *price units per bar* relative to the
chart's **scale** (Rule 08): the 1x1 moves 1 unit of price per bar, the 2x1
moves 2 units per bar, the 1x2 moves half a unit per bar, and so on.

    actual slope of an angle  =  rate x scale   (price change per bar)

where ``rate`` is the angle's multiple of the 1x1 and ``scale`` is the chart
scale (price units per grid square / per bar on the 1x1).

Visual degrees are true only when the chart is drawn with equal scaling
(1 bar horizontally == ``scale`` price units vertically).  See
:func:`gann.chart.plot_gann` which enforces this ("true angle" mode).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

__all__ = [
    "Angle",
    "ANGLES",
    "angle_by_name",
    "angle_line",
    "fan_levels",
    "position_report",
    "suggest_scale",
    "GANN_SCALE_BASES",
]


# ---------------------------------------------------------------------------
# The angle family (Rules 24–33).  Ordered strongest (steepest) to weakest.
# rate = price units per bar per 1 unit of scale (i.e. multiple of the 1x1).
# degrees = visual angle on a correctly scaled chart (Rule 08/M02).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Angle:
    name: str
    rate: float      # price units per bar, per 1.0 of scale
    degrees: float   # visual angle on a properly scaled chart

    def slope(self, scale: float) -> float:
        """Price change per bar on a chart with the given scale."""
        return self.rate * scale


ANGLES: tuple[Angle, ...] = (
    Angle("16x1", 16.0, 86.25),
    Angle("8x1", 8.0, 82.5),
    Angle("4x1", 4.0, 75.0),
    Angle("3x1", 3.0, 71.25),
    Angle("2x1", 2.0, 63.75),
    Angle("3x2", 1.5, 56.25),
    Angle("1x1", 1.0, 45.0),   # the "holy" angle — Rule 24
    Angle("1x2", 0.5, 26.5),   # Rule 30
    Angle("1x4", 0.25, 15.0),  # Rule 31
    Angle("1x8", 0.125, 7.5),  # Rule 32
    Angle("1x16", 0.0625, 3.75),  # Rule 33
)

_BY_NAME = {a.name: a for a in ANGLES}


def angle_by_name(name: str) -> Angle:
    """Look up an angle by its Gann name, e.g. ``'1x1'`` or ``'2x1'``."""
    key = name.strip().replace("×", "x").replace("−", "-")
    if key not in _BY_NAME:
        raise KeyError(f"Unknown Gann angle {name!r}. Valid: {[a.name for a in ANGLES]}")
    return _BY_NAME[key]


# ---------------------------------------------------------------------------
# Rule 08: chart scale must use Gann numbers (1, 2, 4, 8, 10 units per
# square) at some decimal magnitude.
# ---------------------------------------------------------------------------
GANN_SCALE_BASES = (0.5, 1.0, 2.0, 4.0, 5.0, 8.0, 10.0)


def angle_line(
    pivot_bar: int,
    pivot_price: float,
    scale: float,
    angle: Angle | str,
    n_bars: int,
    direction: int = 1,
) -> np.ndarray:
    """Price values of one angle from a pivot across ``n_bars`` bars.

    Values before the pivot are NaN (the angle does not exist yet).
    ``direction=+1`` draws a rising angle from a low (bull fan, Rule 34);
    ``direction=-1`` draws a falling angle from a high (bear fan, Rule 35).
    """
    a = angle_by_name(angle) if isinstance(angle, str) else angle
    if n_bars <= pivot_bar:
        raise ValueError("n_bars must exceed pivot_bar")
    out = np.full(n_bars, np.nan, dtype=float)
    idx = np.arange(pivot_bar, n_bars)
    out[idx] = pivot_price + direction * a.slope(scale) * (idx - pivot_bar)
    return out


def fan_levels(
    pivot_bar: int,
    pivot_price: float,
    scale: float,
    at_bar: int,
    direction: int = 1,
    names: Sequence[str] = ("4x1", "2x1", "1x1", "1x2", "1x4"),
) -> dict[str, float]:
    """Fan prices evaluated at ``at_bar`` — e.g. at the latest bar."""
    return {
        n: float(pivot_price + direction * angle_by_name(n).slope(scale) * (at_bar - pivot_bar))
        for n in names
        if at_bar >= pivot_bar
    }


def position_report(price: float, levels: dict[str, float]) -> str:
    """Describe the market's position vs. the angle fan (Rules 24–33).

    ``levels`` is expected to come from :func:`fan_levels` with the fan drawn
    from the most recent *opposite* pivot (bull fan from a low in an
    uptrend, bear fan from a high in a downtrend).
    """
    if not levels:
        return "no fan"
    ordered = sorted(levels.items(), key=lambda kv: kv[1])
    below = [(n, v) for n, v in ordered if v <= price]   # angles market is ABOVE
    above = [(n, v) for n, v in ordered if v > price]    # angles market is BELOW

    parts: list[str] = []
    if below:
        strongest = below[-1][0]
        parts.append(f"above {strongest} ({below[-1][1]:.2f})")
    if above:
        parts.append(f"below {above[0][0]} ({above[0][1]:.2f})")
    where = " and ".join(parts) if parts else "between angles"

    if "1x1" in levels:
        one = levels["1x1"]
        if price > one:
            verdict = "strong position (Rule 24) — buy zone with stop just below 1x1"
        elif abs(price - one) / max(one, 1e-9) < 0.001:
            verdict = "sitting ON the 1x1 — decision point (Rule 38: first touch usually holds)"
        else:
            verdict = "weak position (below 1x1) — first bounce expected at next lower angle (Rule 30)"
    else:
        verdict = ""
    return f"price {price:.2f} is {where}; {verdict}".strip("; ")


# ---------------------------------------------------------------------------
# Scale selection & verification (Rules 08 & 09)
# ---------------------------------------------------------------------------

def suggest_scale(
    df: pd.DataFrame,
    candidates: Iterable[float] | None = None,
) -> tuple[float, dict]:
    """Pick the chart scale per Rules 08–09.

    Rule 09: the 1x1 drawn from a major low (rising to the major high) must
    land on the 50% retracement of the range for the scale to be "correct".

    Returns ``(scale, diagnostics)`` where diagnostics explains the choice.
    """
    low_idx = int(np.argmin(df["Low"].to_numpy(dtype=float)))
    high_idx = int(np.argmax(df["High"].to_numpy(dtype=float)))
    lo = float(df["Low"].iloc[low_idx])
    hi = float(df["High"].iloc[high_idx])
    midpoint = lo + 0.5 * (hi - lo)

    bars_between = abs(high_idx - low_idx)
    if bars_between < 3:
        bars_between = 3  # need at least 3 bars of movement (Rule 34 spirit)

    ideal = (hi - lo) / 2.0 / bars_between  # slope that puts 1x1 on the 50%

    if candidates is None:
        cands = []
        for mag in (0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0):
            cands.extend(b * mag for b in GANN_SCALE_BASES)
        candidates = cands

    best = min(candidates, key=lambda c: abs(np.log(c / max(ideal, 1e-12))))
    diag = {
        "major_low": (low_idx, lo),
        "major_high": (high_idx, hi),
        "midpoint_50pct": midpoint,
        "bars_between": bars_between,
        "ideal_slope": ideal,
        "scale": best,
        "one_by_one_at_opposite": lo + best * bars_between,
        "miss_vs_50pct": abs((lo + best * bars_between) - midpoint),
    }
    return best, diag
