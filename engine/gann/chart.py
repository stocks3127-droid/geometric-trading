"""Gann chart construction — Rulebook Part 1, Module 02 (Rules 05–10).

* bar/candle chart, trading days only, no blank weekend gaps (Rule 05)
* update space on the right, with angle projections drawn into it (Rule 06)
* chart scale in price units per bar; optional *true-angle* mode forces
  1 bar horizontally == ``scale`` price units vertically so the 1x1 really
  is 45 degrees (Rule 08)
* angle fan from the major pivot (Rules 34–36)
* range-division lines with the 50% king emphasized (Rule 82)
* Square of 9 horizontal levels from the center price (Rule 134)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import square_of_nine as sq9
from . import levels as lv
from .angles import angle_by_name, angle_line, suggest_scale
from .swings import Pivot, major_low_high

__all__ = ["plot_gann"]

FAN_NAMES = ("4x1", "2x1", "1x1", "1x2", "1x4")

_STYLE = None


def _mpf_style():
    global _STYLE
    if _STYLE is None:
        import mplfinance as mpf

        mc = mpf.make_marketcolors(up="#26a69a", down="#ef5350", edge="inherit", wick="inherit", volume="in")
        _STYLE = mpf.make_mpf_style(
            marketcolors=mc,
            mavcolors=["#1565c0"],
            facecolor="white",
            gridcolor="#e0e0e0",
            gridstyle="--",
            rc={"font.size": 9},
        )
    return _STYLE


def _enforce_true_angles(fig, ax, scale: float) -> bool:
    """Rule 08: make 1 bar horizontally == ``scale`` price units vertically.

    Rather than distorting data limits with ``set_aspect`` (mplfinance
    panels are twinned axes and reject it), resize the *figure* so the
    axes box gets exactly the right proportions.  Returns True when the
    45-degree geometry could be enforced within sane sheet bounds
    (4–26 inches tall); a genuine 45-degree sheet can be tall — Gann
    worked on large chart paper.
    """
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    pos = ax.get_position()
    W, _H = fig.get_size_inches()
    xr = max(x1 - x0, 1e-9)
    yr = max(y1 - y0, 1e-9)
    # want: px-per-bar == scale * px-per-price-unit
    #   (pos.width*W)/xr == scale * (pos.height*H)/xr -> solve for H
    target_h = pos.width * W * yr / (scale * xr * pos.height)
    if 4.0 <= target_h <= 26.0:
        fig.set_size_inches(W, target_h)
        return True
    return False


def plot_gann(
    df: pd.DataFrame,
    symbol: str = "SYMBOL",
    scale: float | None = None,
    pivot: Pivot | None = None,
    fan_names: tuple[str, ...] = FAN_NAMES,
    draw_range_levels: bool = True,
    draw_sq9: bool = True,
    sq9_center: float | None = None,
    update_space_pct: float = 12.0,
    true_angles: bool = True,
    save_path: str | Path | None = None,
    show: bool = False,
):
    """Draw the Gann working chart and return ``(fig, axes)``.

    ``scale``      : price units per bar for the 1x1 (Rule 08).  None =
                     suggest via Rules 08/09 (:func:`gann.angles.suggest_scale`).
    ``pivot``      : Pivot the fan is drawn from (Rules 34/35).  None =
                     major low if it leads the major high (bull fan),
                     else the major high (bear fan).
    ``true_angles``: enforce a true 45-degree 1x1 on screen (Rule 08).
    """
    import mplfinance as mpf

    if scale is None:
        scale, _ = suggest_scale(df)

    lo, hi = major_low_high(df)
    if pivot is None:
        pivot = lo if lo.bar <= hi.bar else hi
    direction = 1 if pivot.kind == "L" else -1

    n = len(df)
    extra = max(10, int(n * update_space_pct / 100.0))  # Rule 06 update space

    # ---- fan lines, extended into the update space ----------------------
    fan = {}
    for name in fan_names:
        fan[name] = angle_line(pivot.bar, pivot.price, scale, angle_by_name(name), n + extra, direction)

    # ---- overlays --------------------------------------------------------
    pmin, pmax = float(df["Low"].min()), float(df["High"].max())
    pad = 0.03 * (pmax - pmin + 1e-9)
    y_lo, y_hi = pmin - pad, pmax + pad

    range_lines = lv.range_levels(pmax, pmin) if draw_range_levels else {}

    center = sq9_center if sq9_center is not None else pivot.price
    sq9_lines: list[tuple[float, str]] = []
    if draw_sq9:
        for d in (90, 180, 270, 360):
            v = sq9.price_at_degree(center, d, up=True)
            if y_lo < v < y_hi:
                sq9_lines.append((v, f"sq9 +{d}°"))
            v = sq9.price_at_degree(center, d, up=False)
            if y_lo < v < y_hi:
                sq9_lines.append((v, f"sq9 −{d}°"))

    # ---- render ----------------------------------------------------------
    fig, axes = mpf.plot(
        df,
        type="candle",
        style=_mpf_style(),
        volume=bool(df["Volume"].sum() > 0),
        returnfig=True,
        figsize=(16, 9),
        xrotation=0,
        datetime_format="%d %b %H:%M",
        warn_too_much_data=10000,
    )
    ax = axes[0]
    x = np.arange(n + extra)

    colors = {"1x1": "#d32f2f", "2x1": "#1565c0", "4x1": "#6a1b9a",
              "1x2": "#f9a825", "1x4": "#00897b", "3x2": "#5d4037"}
    for name, line in fan.items():
        ax.plot(x, line, lw=1.4 if name == "1x1" else 0.9, ls="-" if name == "1x1" else "--",
                color=colors.get(name, "#757575"), alpha=0.9)
        last = line[-1]
        if not np.isnan(last):
            ax.annotate(f" {name}", (x[-1], last), fontsize=8,
                        color=colors.get(name, "#757575"), va="center")

    # 50% king line (Rule 82) + minor range divisions
    mid = range_lines.get("1/2 (KING)")
    if mid is not None:
        ax.axhline(mid, color="#b71c1c", lw=1.6, ls="-.")
        ax.annotate(f" 50% KING {mid:.1f}", (0.995, mid), xycoords=("axes fraction", "data"),
                    ha="right", va="bottom", fontsize=8, color="#b71c1c", fontweight="bold")
    for lbl, v in range_lines.items():
        if not lbl.startswith("1/2"):
            ax.axhline(v, color="#9e9e9e", lw=0.7, ls=":")

    for v, lbl in sq9_lines:
        ax.axhline(v, color="#00695c", lw=0.8, ls=":")
        ax.annotate(f" {lbl} {v:.1f}", (x[-1] - 0.2, v), fontsize=7, color="#00695c", va="center")

    # pivot marker
    ax.scatter([pivot.bar], [pivot.price], marker="*" if pivot.kind == "L" else "v",
               s=120, color="#b71c1c", zorder=5)

    ax.set_xlim(-1, n + extra)
    ax.set_ylim(y_lo, y_hi)
    if true_angles and _enforce_true_angles(fig, ax, scale):
        angle_note = " | TRUE 45° (1 bar = scale units)"
    else:
        angle_note = " | angles not visually calibrated (numbers still exact)"

    t0, t1 = df.index[0], df.index[-1]
    ax.set_title(
        f"{symbol} — Gann working chart | scale {scale:g}/bar{angle_note} | fan from "
        f"{'LOW' if pivot.kind == 'L' else 'HIGH'} {pivot.price:.2f} "
        f"({pivot.index:%d %b %H:%M}) | {t0:%d %b} → {t1:%d %b %Y}"
    )

    if save_path is not None:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig, axes
