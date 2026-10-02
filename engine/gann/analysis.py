"""Full Gann workup of an OHLCV frame — ties every module together.

Follows the pre-trade checklist flow of the rulebook: trend (M03) →
scale (M02 Rules 08/09) → angle fan & position (M04) → S/R (M08) →
Square of 9 (M11) → time factor (M12, Rule 135/138/171).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from . import levels as lv
from . import square_of_nine as sq9
from . import timing
from .angles import fan_levels, position_report, suggest_scale
from .swings import major_low_high, trend, zigzag


def analyze(df: pd.DataFrame, pct: float = 0.5) -> dict:
    """Run the full analysis; returns a plain dict ready for formatting."""
    lo, hi = major_low_high(df)
    pivots = zigzag(df, pct=pct)
    tr, reason = trend(pivots)
    scale, diag = suggest_scale(df)

    # Rule 34/35: bull fan from a low that leads the high; bear fan otherwise
    pivot = lo if lo.bar <= hi.bar else hi
    direction = 1 if pivot.kind == "L" else -1
    last_bar = len(df) - 1
    fan = fan_levels(pivot.bar, pivot.price, scale, last_bar, direction)
    price = float(df["Close"].iloc[-1])

    range_lvls = lv.range_levels(hi.price, lo.price)
    nearest = lv.nearest(price, range_lvls, k=6)

    # Rule 134/121: set the Square of 9 center on the contract/major low
    center = lo.price if lo.price > 0 else price
    wheel = sq9.levels_around(center, price)

    # confluence: range divisions meeting wheel levels within 0.15%
    wheel_map = {f"sq9 {d:.0f}°": p for d, p in wheel["resistance"] + wheel["support"]}
    clusters = [c for c in lv.confluence(range_lvls, wheel_map, tol_pct=0.15) if len(c[1]) > 1]

    # Time factor — Rule 135/138 from the major low date; Rule 171 intraday
    cycles = timing.calendar_cycles(lo.index.date())
    intraday: list[tuple[datetime, int, int]] = []
    last_day = df.index[df.index.date == df.index[-1].date()]
    if len(last_day):
        intraday = timing.intraday_cycles(last_day[0].to_pydatetime())

    return {
        "bars": len(df),
        "from": df.index[0],
        "to": df.index[-1],
        "price": price,
        "trend": tr,
        "trend_reason": reason,
        "pivots": pivots[-6:],
        "major_low": lo,
        "major_high": hi,
        "scale": scale,
        "scale_diag": diag,
        "fan_pivot": pivot,
        "fan": fan,
        "position": position_report(price, fan),
        "range_levels": range_lvls,
        "nearest_levels": nearest,
        "sq9_center": center,
        "sq9_resistance": wheel["resistance"][:5],
        "sq9_support": wheel["support"][:5],
        "confluence": clusters,
        "time_cycles": cycles,
        "intraday_cycles": intraday,
    }


def format_report(res: dict, symbol: str, interval: str) -> str:
    """Render the analysis dict as the classic pre-trade checklist text."""
    w = 78
    out: list[str] = []
    add = out.append
    add("=" * w)
    add(f"GANN WORKUP — {symbol} ({interval})".center(w))
    add("=" * w)
    add(f"bars {res['bars']} | {res['from']:%d %b %Y %H:%M} → {res['to']:%d %b %Y %H:%M} | close {res['price']:.2f}")
    add("")

    add("[1] TREND (M03) — all timeframes must align")
    add(f"    {res['trend']}  ({res['trend_reason']})")
    add("    last swings: " + "  ".join(
        f"{'H' if p.kind == 'H' else 'L'} {p.price:.1f} @{p.index:%d %b %H:%M}" for p in res["pivots"][-4:]
    ))
    add("")

    lo, hi = res["major_low"], res["major_high"]
    add("[2] RANGE & 50% KING (M08 Rule 82)")
    add(f"    major low {lo.price:.2f} @{lo.index:%d %b %H:%M} | major high {hi.price:.2f} @{hi.index:%d %b %H:%M}")
    mid = res["range_levels"].get("1/2 (KING)")
    add(f"    50% KING level: {mid:.2f}" + ("  <- price is ON the king level" if abs(res["price"] - mid) / mid < 0.002 else ""))
    add("")

    add("[3] CHART SCALE (M02 Rules 08–09)")
    d = res["scale_diag"]
    add(f"    scale {res['scale']:g} price-units/bar | ideal 1x1 slope {d['ideal_slope']:.4f}")
    add(f"    1x1 from low reaches {d['one_by_one_at_opposite']:.2f} vs 50% {d['midpoint_50pct']:.2f} (miss {d['miss_vs_50pct']:.2f})")
    add("")

    add("[4] ANGLE FAN & POSITION (M04 Rules 24–38)")
    p = res["fan_pivot"]
    add(f"    fan from {'LOW' if p.kind == 'L' else 'HIGH'} {p.price:.2f} @{p.index:%d %b %H:%M}:")
    for name, v in sorted(res["fan"].items(), key=lambda kv: -kv[1]):
        marker = "  <-- price" if abs(v - res["price"]) == min(abs(x - res["price"]) for x in res["fan"].values()) else ""
        add(f"      {name:>4}: {v:10.2f}{marker}")
    add(f"    position: {res['position']}")
    add("")

    add("[5] NEAREST S/R — range divisions (M08)")
    for lbl, v, dist in res["nearest_levels"]:
        add(f"    {lbl:>10}: {v:10.2f}  ({dist:+.2f})")
    add("")

    add(f"[6] SQUARE OF 9 (M11 Rules 134–138) — center (major low) {res['sq9_center']:.2f}")
    add("    resistance: " + "  ".join(f"{d}°→{v:.2f}" for d, v in res["sq9_resistance"]))
    add("    support:    " + "  ".join(f"{d}°→{v:.2f}" for d, v in res["sq9_support"]))
    if res["confluence"]:
        add("    CONFLUENCE with range divisions:")
        for v, lbls in res["confluence"]:
            add(f"      {v:10.2f}  <- {' + '.join(lbls)}")
    add("")

    add("[7] TIME FACTOR (M12 Rules 135/138) from major low date")
    if res["time_cycles"]:
        for dt, days, rank in res["time_cycles"]:
            add(f"    {dt:%a %d %b %Y}  +{days:>3}d  (rank {rank})")
    else:
        add("    (no upcoming circle dates inside the 366-day horizon)")
    add("")
    add("[8] INTRADAY TIME (Rule 171) — circle minutes from last session open")
    if res["intraday_cycles"]:
        add("    " + "  ".join(f"{dt:%H:%M} (+{m}m r{r})" for dt, m, r in res["intraday_cycles"]))
    add("")
    add("Rule 1 (M01): capital preservation first — size stops before targets.")
    add("=" * w)
    return "\n".join(out)
