"""Swing charts & trend identification — Rulebook Part 1, Module 03 and
Part 2, Module 14 (Swing Charts).

A minimal zigzag pivot detector: a swing high/low is confirmed after price
retraces more than ``pct`` (or ``abs_pts``) from the running extreme.
Trend (M03) = last two swing highs + last two swing lows:

    higher high + higher low  -> UP
    lower high  + lower low   -> DOWN
    anything mixed             -> SIDE
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

__all__ = ["Pivot", "zigzag", "trend", "last_pivots"]

PivotKind = Literal["H", "L"]


@dataclass(frozen=True)
class Pivot:
    bar: int
    index: pd.Timestamp
    price: float
    kind: PivotKind

    @property
    def is_low(self) -> bool:
        return self.kind == "L"


def zigzag(df: pd.DataFrame, pct: float = 0.5, abs_pts: float | None = None) -> list[Pivot]:
    """Detect alternating swing highs/lows on an OHLC frame.

    ``pct``: reversal threshold as % of the running extreme price.
    ``abs_pts``: optional absolute price-point override.
    """
    highs = df["High"].to_numpy(dtype=float)
    lows = df["Low"].to_numpy(dtype=float)
    n = len(df)
    if n < 3:
        return []

    def reversed_from(extreme: float, price: float) -> bool:
        d = abs(extreme - price)
        if abs_pts is not None:
            return d >= abs_pts
        return d / max(abs(extreme), 1e-12) * 100.0 >= pct

    def extreme_between(arr: np.ndarray, start: int, end: int, want_min: bool) -> tuple[int, float]:
        seg = arr[start : end + 1]
        i = int(np.argmin(seg)) if want_min else int(np.argmax(seg))
        return start + i, float(seg[i])

    pivots: list[Pivot] = []
    direction = 0  # 0 undecided, +1 up (tracking a high), -1 down (tracking a low)
    hi_i, hi_p = 0, highs[0]
    lo_i, lo_p = 0, lows[0]
    ext_i, ext_p = -1, float("nan")

    for i in range(1, n):
        if direction == 0:
            if highs[i] > hi_p:
                hi_i, hi_p = i, highs[i]
            if lows[i] < lo_p:
                lo_i, lo_p = i, lows[i]
            if reversed_from(hi_p, lows[i]):  # fell far enough off the running high
                pivots.append(Pivot(hi_i, df.index[hi_i], hi_p, "H"))
                direction = -1
                if hi_i >= i:  # wide-range bar confirmed itself as the pivot
                    ext_i, ext_p = i, lows[i]
                else:
                    ext_i, ext_p = extreme_between(lows, hi_i + 1, i, want_min=True)
            elif reversed_from(lo_p, highs[i]):  # rallied far enough off the running low
                pivots.append(Pivot(lo_i, df.index[lo_i], lo_p, "L"))
                direction = 1
                if lo_i >= i:
                    ext_i, ext_p = i, highs[i]
                else:
                    ext_i, ext_p = extreme_between(highs, lo_i + 1, i, want_min=False)
        elif direction == -1:  # downswing: track the running low
            if lows[i] <= ext_p:
                ext_i, ext_p = i, lows[i]
            elif reversed_from(ext_p, highs[i]):
                pivots.append(Pivot(ext_i, df.index[ext_i], ext_p, "L"))
                direction = 1
                ext_i, ext_p = i, highs[i]
        else:  # upswing: track the running high
            if highs[i] >= ext_p:
                ext_i, ext_p = i, highs[i]
            elif reversed_from(ext_p, lows[i]):
                pivots.append(Pivot(ext_i, df.index[ext_i], ext_p, "H"))
                direction = -1
                ext_i, ext_p = i, lows[i]

    # provisional extreme at the right edge (not yet confirmed by a reversal)
    if ext_i >= 0:
        kind: PivotKind = "L" if direction == -1 else "H"
        if pivots and pivots[-1].kind != kind:
            pivots.append(Pivot(ext_i, df.index[ext_i], ext_p, kind))
        elif not pivots:
            pivots.append(Pivot(ext_i, df.index[ext_i], ext_p, kind))

    # enforce strict alternation H, L, H, L...
    cleaned: list[Pivot] = []
    for p in pivots:
        if cleaned and cleaned[-1].kind == p.kind:
            # keep the more extreme of two same-kind pivots
            if (p.kind == "H" and p.price >= cleaned[-1].price) or (
                p.kind == "L" and p.price <= cleaned[-1].price
            ):
                cleaned[-1] = p
        else:
            cleaned.append(p)
    return cleaned


def last_pivots(pivots: list[Pivot], k: int = 4) -> list[Pivot]:
    return pivots[-k:] if len(pivots) >= k else pivots


def trend(pivots: list[Pivot]) -> tuple[str, str]:
    """M03 trend call from the swing chart.

    Returns ``(trend, reason)`` where trend is 'UP', 'DOWN' or 'SIDE'.
    """
    highs = [p for p in pivots if p.kind == "H"][-2:]
    lows = [p for p in pivots if p.kind == "L"][-2:]
    if len(highs) < 2 or len(lows) < 2:
        return "SIDE", "not enough confirmed swings"
    hh = highs[1].price > highs[0].price
    hl = lows[1].price > lows[0].price
    lh = highs[1].price < highs[0].price
    ll = lows[1].price < lows[0].price
    if hh and hl:
        return "UP", f"HH {highs[0].price:.1f}->{highs[1].price:.1f} + HL {lows[0].price:.1f}->{lows[1].price:.1f}"
    if lh and ll:
        return "DOWN", f"LH {highs[0].price:.1f}->{highs[1].price:.1f} + LL {lows[0].price:.1f}->{lows[1].price:.1f}"
    return "SIDE", "mixed swings (HH+LL or LH+HL) — wait for confirmation"


def major_low_high(df: pd.DataFrame) -> tuple[Pivot, Pivot]:
    """Absolute major low and major high of the window (for scale + fan)."""
    li = int(np.argmin(df["Low"].to_numpy(dtype=float)))
    hi = int(np.argmax(df["High"].to_numpy(dtype=float)))
    lo = Pivot(li, df.index[li], float(df["Low"].iloc[li]), "L")
    hi_p = Pivot(hi, df.index[hi], float(df["High"].iloc[hi]), "H")
    return lo, hi_p
