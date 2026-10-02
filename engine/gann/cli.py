"""CLI for the Gann engine.

    python -m gann analyze RELIANCE --days 30 --interval 5m
    python -m gann sq9 496
    python -m gann timing 2026-08-01
    python -m gann demo
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from . import data, timing
from . import square_of_nine as sq9
from .analysis import analyze, format_report


def _cmd_analyze(args) -> int:
    df = data.fetch(args.symbol, days=args.days, interval=args.interval, source=args.source)
    res = analyze(df, pct=args.pct)
    print(format_report(res, args.symbol.upper(), args.interval))
    out = Path(args.out) / f"{args.symbol.upper()}_{args.interval}_{df.index[-1]:%Y%m%d}.png"
    from .chart import plot_gann  # lazy: needs mplfinance

    plot_gann(
        df, symbol=args.symbol.upper(), scale=args.scale or None,
        pivot=None, save_path=out, true_angles=not args.no_true_angles,
    )
    print(f"\nChart saved: {out}")
    return 0


def _cmd_sq9(args) -> int:
    center = args.center if args.center else args.price
    price = args.price if args.center else None
    res = sq9.levels_around(center, price)
    print(f"SQUARE OF 9 — center {center:g}  (Rule 134; 360° = +2 on the square root)")
    print(f"{'':2}{'degrees':>8} {'price':>12}")
    for d, v in res["resistance"]:
        print(f"  +{d:>7.0f} {v:>12.2f}   resistance above")
    for d, v in res["support"]:
        print(f"  −{d:>7.0f} {v:>12.2f}   support below")
    print("\nRule 138 ranks: 90(1) 45(2) 180(3) 135(4) 270(5) 120(6) 315(7) 225(8) 144(9) 216(10)")
    return 0


def _cmd_timing(args) -> int:
    start = datetime.strptime(args.date, "%Y-%m-%d").date()
    print(f"TIME CYCLES (Rules 135/138) from pivot date {start:%d %b %Y}")
    rows = timing.calendar_cycles(start, horizon_days=args.horizon)
    for dt, days, rank in rows:
        print(f"  {dt:%a %d %b %Y}  +{days:>3} days  rank {rank}")
    if not rows:
        print("  (none inside the horizon — all circle dates are past or too far)")
    print("\nAnniversaries (Rule 139):")
    for dt in timing.anniversary_dates(start, years=3):
        print(f"  {dt:%a %d %b %Y}")
    return 0


def _cmd_demo(args) -> int:
    print(f"DEMO — synthetic NSE-like series (seed {args.seed}), no network needed")
    df = data.synthetic(symbol="DEMO", days=args.days, interval=args.interval, seed=args.seed)
    res = analyze(df, pct=args.pct)
    print(format_report(res, "DEMO-NIFTY", args.interval))
    out = Path(args.out) / f"demo_{args.interval}_seed{args.seed}.png"
    from .chart import plot_gann

    plot_gann(df, symbol="DEMO-NIFTY", save_path=out, true_angles=not args.no_true_angles)
    print(f"\nChart saved: {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gann", description="Gann geometric trading engine (NSE)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("analyze", help="full workup + chart for an NSE symbol")
    p.add_argument("symbol")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--interval", default="5m", choices=["1m", "2m", "5m", "15m", "30m", "60m", "1d"])
    p.add_argument("--source", default="auto", choices=["auto", "yfinance", "jugaad", "synthetic"])
    p.add_argument("--pct", type=float, default=0.5, help="zigzag reversal %% for swing detection")
    p.add_argument("--scale", type=float, default=0.0, help="override price units/bar (0 = suggest)")
    p.add_argument("--out", default="charts", help="chart output dir")
    p.add_argument("--no-true-angles", action="store_true", help="don't force 45-degree rendering")
    p.set_defaults(func=_cmd_analyze)

    p = sub.add_parser("sq9", help="Square of 9 levels around a price")
    p.add_argument("price", type=float, help="reference price (or the low to centre on)")
    p.add_argument("--center", type=float, default=None, help="wheel center (default: the price itself)")
    p.set_defaults(func=_cmd_sq9)

    p = sub.add_parser("timing", help="time-cycle dates from a pivot date")
    p.add_argument("date", help="pivot date YYYY-MM-DD")
    p.add_argument("--horizon", type=int, default=366)
    p.set_defaults(func=_cmd_timing)

    p = sub.add_parser("demo", help="offline demo on synthetic data")
    p.add_argument("--days", type=int, default=15)
    p.add_argument("--interval", default="15m", choices=["5m", "15m", "30m", "60m"])
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--pct", type=float, default=0.5)
    p.add_argument("--out", default="charts")
    p.add_argument("--no-true-angles", action="store_true")
    p.set_defaults(func=_cmd_demo)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
