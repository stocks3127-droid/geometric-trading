#!/usr/bin/env python3
"""End-to-end API tour of the Gann engine (offline by default).

    cd engine && source .venv/bin/activate
    python examples/demo_intraday.py            # synthetic, no network
    python examples/demo_intraday.py --live \    # real NSE 15m data
        --symbol RELIANCE --days 20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # engine/

from gann import data  # noqa: E402
from gann.analysis import analyze, format_report  # noqa: E402
from gann.chart import plot_gann  # noqa: E402
from gann.square_of_nine import price_at_degree  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="RELIANCE")
    ap.add_argument("--days", type=int, default=15)
    ap.add_argument("--interval", default="15m", choices=["1m", "5m", "15m", "30m", "60m", "1d"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--live", action="store_true", help="fetch real NSE data (needs network)")
    args = ap.parse_args()

    # ---- 1. data ----------------------------------------------------------
    df = data.fetch(
        args.symbol,
        days=args.days,
        interval=args.interval,
        source="auto" if args.live else "synthetic",
    )
    print(f"data: {len(df)} bars, {df.index[0]} -> {df.index[-1]}")

    # ---- 2. full workup ---------------------------------------------------
    res = analyze(df, pct=0.5)
    print(format_report(res, args.symbol.upper(), args.interval))

    # ---- 3. one Square of 9 projection by hand (Rule 134) -----------------
    lo = res["major_low"].price
    print(f"\nRule 134 quick check — Square of 9 wheel centered on low {lo:.2f}:")
    for d in (45, 90, 135, 180, 270, 360):
        print(f"  +{d:>3}°  ->  {price_at_degree(lo, d, up=True):.2f}")

    # ---- 4. chart ---------------------------------------------------------
    out = Path(__file__).resolve().parents[1] / "charts" / "demo_api.png"
    plot_gann(df, symbol=args.symbol.upper(), save_path=out)
    print(f"\nchart saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
