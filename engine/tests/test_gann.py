"""Engine tests — anchored to the rulebook's own worked examples.

Run:  pytest -q          (from engine/)
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from gann import angles, levels, square_of_nine as sq9, swings, timing
from gann.angles import angle_line, fan_levels, suggest_scale
from gann.data import synthetic
from gann.swings import zigzag, trend


# ---------------------------------------------------------------------------
# Square of 9 — Rule 134 worked example (center 496)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("deg,expected", [(45, 507), (90, 518), (180, 541)])
def test_sq9_rule134_resistance(deg, expected):
    got = sq9.price_at_degree(496, deg, up=True)
    assert abs(got - expected) <= 1.0, f"45/90/180 up: got {got:.1f}, rulebook {expected}"


@pytest.mark.parametrize("deg,expected", [(45, 485), (90, 474), (180, 452)])
def test_sq9_rule134_support(deg, expected):
    got = sq9.price_at_degree(496, deg, up=False)
    assert abs(got - expected) <= 1.0, f"down: got {got:.1f}, rulebook {expected}"


def test_sq9_full_rotation_adds_two_to_root():
    p = 225.0
    full = sq9.price_at_degree(p, 360, up=True)
    assert full == pytest.approx((math.sqrt(p) + 2) ** 2, rel=1e-12)


def test_sq9_levels_around_sorted_by_distance():
    out = sq9.levels_around(1000.0, price=1005.0)
    dists = [abs(v - 1005.0) for _, v in out["resistance"]]
    assert dists == sorted(dists)
    assert all(v > 1005.0 for _, v in out["resistance"])
    assert all(v < 1005.0 for _, v in out["support"])


def test_sq9_degrees_position_inverse():
    center = 496.0
    up45 = sq9.price_at_degree(center, 45, up=True)
    assert sq9.degrees_position(up45, center) == pytest.approx(45.0, abs=0.01)
    dn90 = sq9.price_at_degree(center, 90, up=False)
    assert sq9.degrees_position(dn90, center) == pytest.approx(-90.0, abs=0.01)


# Rule 130/131 — circle ends
def test_circle_ends():
    assert sq9.circle_ends("sq9", 6) == [9, 25, 49, 81, 121, 169]
    assert sq9.circle_ends("sq4", 5) == [4, 16, 36, 64, 100]


# Rule 132/133 — cross sequences (first five terms match the rulebook)
@pytest.mark.parametrize("arm,expected", [
    ("N", [4, 15, 34, 61, 96]),
    ("E", [6, 19, 40, 69, 106]),
    ("S", [8, 23, 46, 77, 116]),
    ("W", [2, 11, 28, 53, 86]),
])
def test_cardinal_cross(arm, expected):
    assert sq9.cardinal_cross(rings=5)[arm] == expected


@pytest.mark.parametrize("arm,expected", [
    ("NW", [3, 13, 31, 57, 91]),
    ("SE", [7, 21, 43, 73, 111]),
])
def test_diagonal_cross(arm, expected):
    assert sq9.diagonal_cross(rings=5)[arm] == expected


@pytest.mark.parametrize("num,ring", [(1, 0), (9, 1), (10, 2), (25, 2), (26, 3), (49, 3), (50, 4)])
def test_ring_of(num, ring):
    assert sq9.ring_of(num) == ring


# ---------------------------------------------------------------------------
# Angles — Module 04
# ---------------------------------------------------------------------------

def test_angle_table_degrees():
    assert angles.angle_by_name("1x1").degrees == 45.0
    assert angles.angle_by_name("2x1").degrees == 63.75
    assert angles.angle_by_name("4x1").degrees == 75.0
    assert angles.angle_by_name("8x1").degrees == 82.5
    assert angles.angle_by_name("1x2").degrees == 26.5
    assert angles.angle_by_name("1x8").degrees == 7.5


def test_angle_line_from_low():
    line = angle_line(10, 100.0, scale=2.0, angle="1x1", n_bars=21)
    assert np.isnan(line[9])
    assert line[10] == 100.0
    assert line[20] == pytest.approx(120.0)  # 10 bars * 2/bar


def test_angle_line_bear_fan():
    line = angle_line(0, 200.0, scale=1.0, angle="2x1", n_bars=11, direction=-1)
    assert line[10] == pytest.approx(180.0)


def test_fan_levels_ordering():
    fan = fan_levels(0, 100.0, scale=1.0, at_bar=10)
    assert fan["4x1"] > fan["2x1"] > fan["1x1"] > fan["1x2"] > fan["1x4"]


def test_position_report_language():
    fan = {"4x1": 140.0, "2x1": 120.0, "1x1": 110.0, "1x2": 95.0, "1x4": 90.0}
    strong = angles.position_report(115.0, fan)
    assert "strong position" in strong
    weak = angles.position_report(105.0, fan)
    assert "weak" in weak


def test_suggest_scale_rule09():
    # low ~99 @ bar 0, high ~201 @ bar 100 -> 1x1 slope hitting the 50% ~ 0.51/bar
    idx = pd.date_range("2026-01-01", periods=101, freq="D")
    df = pd.DataFrame(
        {
            "Open": np.linspace(100, 200, 101),
            "High": np.linspace(100, 200, 101) + 1,
            "Low": np.linspace(100, 200, 101) - 1,
            "Close": np.linspace(100, 200, 101),
            "Volume": np.zeros(101),
        },
        index=idx,
    )
    scale, diag = suggest_scale(df)
    lo_price = df["Low"].min()
    hi_price = df["High"].max()
    bars = diag["bars_between"]
    assert diag["ideal_slope"] == pytest.approx((hi_price - lo_price) / 2 / bars, rel=0.01)
    # snapped to a Gann-number magnitude near the ideal slope
    assert 0.25 <= scale <= 1.0
    # Rule 09: the 1x1 at the chosen scale lands close to the 50% level
    assert diag["miss_vs_50pct"] <= 0.25 * (hi_price - lo_price)


# ---------------------------------------------------------------------------
# S/R levels — Module 08, Rule 82
# ---------------------------------------------------------------------------

def test_range_levels_king_is_midpoint():
    out = levels.range_levels(200.0, 100.0)
    assert out["1/2 (KING)"] == 150.0
    assert out["1/3"] == pytest.approx(133.333, abs=0.01)
    assert out["2/3"] == pytest.approx(166.667, abs=0.01)
    assert out["1/4"] == 125.0 and out["3/4"] == 175.0


def test_ath_atl_rules_86_87():
    assert levels.ath_levels(900.0) == {"ATH/3": 300.0, "ATH/2": 450.0}
    assert levels.atl_multiples(50.0) == {"ATL x2": 100.0, "ATL x3": 150.0, "ATL x4": 200.0}


def test_nearest():
    out = levels.nearest(150.0, {"a": 100.0, "b": 148.0, "c": 190.0}, k=2)
    assert out[0][0] == "b"


def test_confluence():
    clusters = levels.confluence({"50%": 150.0}, {"sq9 90°": 150.6}, tol_pct=0.5)
    assert len(clusters[-1][1]) == 2


# ---------------------------------------------------------------------------
# Timing — Module 12
# ---------------------------------------------------------------------------

def test_calendar_cycles_rule135():
    # pure day arithmetic: pivot + N calendar days (rulebook's Mar-21 example
    # is equinox-anchored; the engine uses plain Rule-135 day counts)
    start = date(2026, 3, 21)
    assert start + pd.Timedelta(days=45) == date(2026, 5, 5)
    assert start + pd.Timedelta(days=90) == date(2026, 6, 19)
    assert start + pd.Timedelta(days=180) == date(2026, 9, 17)
    # the function itself: a recent pivot yields future, sorted, ranked dates
    recent = date.today() - pd.Timedelta(days=10)
    rows = timing.calendar_cycles(recent, horizon_days=400)
    assert rows, "all 11 circle dates should still be in the future"
    dates = [r[0] for r in rows]
    assert dates == sorted(dates)
    for (d, days, rank) in rows:
        assert d == recent + pd.Timedelta(days=days)
        assert rank == timing.CYCLE_RANKS[days]


def test_cycle_ranks_rule138():
    assert timing.CYCLE_RANKS[90] == 1
    assert timing.CYCLE_RANKS[45] == 2
    assert timing.CYCLE_RANKS[180] == 3
    assert timing.CYCLE_RANKS[216] == 10


def test_anniversary_rule139():
    out = timing.anniversary_dates(date(2020, 6, 15), years=3)
    assert all(d.month == 6 and d.day == 15 for d in out)


# ---------------------------------------------------------------------------
# Swings & trend — Modules 03/14
# ---------------------------------------------------------------------------

def _frame(closes, start="2026-01-01"):
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {
            "Open": closes,
            "High": closes * 1.002,
            "Low": closes * 0.998,
            "Close": closes,
            "Volume": np.ones(len(closes)),
        },
        index=pd.date_range(start, periods=len(closes), freq="D"),
    )


def test_zigzag_finds_pivots_and_trend_up():
    # up 100->150, down to 125, up to 175
    closes = list(np.linspace(100, 150, 30)) + list(np.linspace(150, 125, 20)) + list(np.linspace(125, 175, 30))
    df = _frame(closes)
    pivots = zigzag(df, pct=5.0)
    kinds = "".join(p.kind for p in pivots)
    assert "H" in kinds and "L" in kinds
    assert kinds in ("HL", "LH") or set(kinds[:2]) == {"H", "L"}
    tr, _ = trend(pivots)
    assert tr in ("UP", "SIDE")


def test_zigzag_alternation():
    closes = list(np.linspace(100, 180, 40)) + list(np.linspace(180, 120, 40)) + list(np.linspace(120, 200, 40))
    pivots = zigzag(_frame(closes), pct=4.0)
    for a, b in zip(pivots, pivots[1:]):
        assert a.kind != b.kind, "pivots must strictly alternate H/L"


def test_major_low_high():
    closes = list(np.linspace(100, 180, 40)) + list(np.linspace(180, 120, 40))
    df = _frame(closes)
    lo, hi = swings.major_low_high(df)
    assert lo.price == pytest.approx(min(closes) * 0.998)
    assert hi.price == pytest.approx(max(closes) * 1.002)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def test_synthetic_shape_and_integrity():
    df = synthetic(days=5, interval="15m", seed=7)
    assert len(df) == 5 * 25
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert (df["High"] >= df[["Open", "Close"]].max(axis=1) - 1e-9).all()
    assert (df["Low"] <= df[["Open", "Close"]].min(axis=1) + 1e-9).all()
    assert df.index.tz is not None
    # weekends excluded
    assert all(ts.weekday() < 5 for ts in df.index)
    # deterministic
    assert synthetic(days=5, interval="15m", seed=7).equals(df)


# ---------------------------------------------------------------------------
# Chart smoke test (needs mplfinance)
# ---------------------------------------------------------------------------

def test_plot_gann_saves_png(tmp_path):
    mpf = pytest.importorskip("mplfinance")
    from gann.chart import plot_gann

    df = synthetic(days=4, interval="30m", seed=3)
    out = tmp_path / "chart.png"
    plot_gann(df, symbol="TEST", save_path=out, true_angles=False)
    assert out.exists() and out.stat().st_size > 10_000


def test_analysis_end_to_end():
    from gann.analysis import analyze, format_report

    df = synthetic(days=6, interval="30m", seed=11)
    res = analyze(df, pct=0.4)
    text = format_report(res, "TEST", "30m")
    assert "TREND" in text and "50% KING" in text and "SQUARE OF 9" in text
    assert res["fan"] and res["scale"] > 0
