# 📐 Gann Engine — companion code for the Rulebook

Executable companion to **Gann Market Geometry Rulebook Parts 1 & 2**
(251 rules). Every module is pinned to the exact rule numbers it
implements, so you can audit the math against the book.

```
┌────────────────────┬──────────────────────────────────────────────────────┐
│ module             │ implements (rulebook reference)                      │
├────────────────────┼──────────────────────────────────────────────────────┤
│ gann/angles.py     │ M04 Rules 24–42  — angle family, fans, scale         │
│                    │ Rules 08/09 — scale selection & 50% verification     │
│ gann/square_of_nine│ M10 Rule 115, M11 Rules 130–139 — SQ9/SQ4 wheels,    │
│                    │ cardinal/diagonal crosses, degree-price rotation     │
│ gann/levels.py     │ M08 Rules 82–87 — range divisions, 50% KING, ATH/ATL │
│ gann/timing.py     │ M12 Rules 135/138/139 + Rule 171 — time cycles       │
│ gann/swings.py     │ M03 + M14 — zigzag pivots, trend calls               │
│ gann/chart.py      │ M02 Rules 05–10 — Gann-scaled charts, update space,  │
│                    │ true 45° rendering                                   │
│ gann/data.py       │ NSE data: yfinance (intraday) / jugaad-data (EOD) /  │
│                    │ offline synthetic                                    │
│ gann/analysis.py   │ the full pre-trade workup (checklist order)          │
│ gann/cli.py        │ command line                                         │
└────────────────────┴──────────────────────────────────────────────────────┘
```

## Quickstart

```bash
cd engine
./setup.sh                     # creates .venv, installs deps

# offline demo (synthetic NSE-like data — no network needed)
.venv/bin/python -m gann demo

# live NSE intraday workup + chart  (needs `pip install yfinance`)
.venv/bin/python -m gann analyze RELIANCE --days 20 --interval 15m
.venv/bin/python -m gann analyze NIFTY_BEES.NS --days 5 --interval 5m

# the rulebook's own Rule 134 example
.venv/bin/python -m gann sq9 496
#   center on a major low instead:
.venv/bin/python -m gann sq9 24456 --center 24456

# time cycles from a pivot date
.venv/bin/python -m gann timing 2026-08-01

# run the test suite (42 tests, several anchored to rulebook examples)
.venv/bin/pytest -q
```

Charts are written to `engine/charts/`.

## The Square of 9 math (Rule 134)

The wheel's engine is the square-root rotation — one full 360° adds **2**
to the square root:

```
price(d°) = (√center ± d/180)²
```

Verified against the rulebook's worked example (center **496**):

| degrees | up (resistance) | down (support) |
|--------:|----------------:|---------------:|
| 45°     | 507 ✓           | 485 ✓          |
| 90°     | 518 ✓           | 474 ✓          |
| 180°    | 541 ✓           | 452 ✓          |

> Note: the rulebook's "120°" figures (529 / 463) correspond to **135°**
> (√-delta 0.75) in the standard formula; both 120° and 135° are emitted
> so you can follow either convention.

## Chart scale & true 45° (Rules 08–09)

`suggest_scale()` picks the price-units-per-bar scale so that the 1×1
from the major low lands on the **50% retracement** (Rule 09), snapped to
Gann-number magnitudes (Rule 08). With `true_angles=True` (default) the
figure is resized so 1 bar on screen == `scale` price units — the 1×1 is
a *genuine* 45°, like Gann's own chart paper. When the required sheet
size exceeds sane bounds the chart notes that angles are not visually
calibrated (the price levels remain mathematically exact).

## Data sources

| source       | use                                            | install            |
|--------------|------------------------------------------------|--------------------|
| `yfinance`   | NSE intraday 1m–60m (≤60 days) & daily        | `pip install yfinance` |
| `jugaad`     | NSE **EOD** history straight from NSE          | `pip install jugaad-data` — [jugaad-py/jugaad-data](https://github.com/jugaad-py/jugaad-data) |
| `synthetic`  | deterministic offline series (demo/tests)      | — |

`source="auto"` tries yfinance → jugaad → synthetic (with a warning), so
the engine never hard-fails offline. For tick/second data or order
execution see [zerodha/pykiteconnect](https://github.com/zerodha/pykiteconnect);
for daily stock scanning see [pkjmesra/PKScreener](https://github.com/pkjmesra/PKScreener).

## Library use

```python
from gann import data
from gann.analysis import analyze, format_report
from gann.chart import plot_gann
from gann.square_of_nine import price_at_degree

df = data.fetch("RELIANCE", days=20, interval="15m")   # auto source
res = analyze(df)                                      # full workup dict
print(format_report(res, "RELIANCE", "15m"))
plot_gann(df, symbol="RELIANCE", save_path="charts/reliance.png")

price_at_degree(24456, 90, up=True)   # Square of 9 resistance 90° above 24456
```

## Status & disclaimers

Engineering complete for the modules above; rulebook coverage will grow
(Elliott wave counts, overlay grids, hexagon/octagon charts are next).
Rule 1 of the rulebook applies to the code too: **capital preservation
first** — this is an analysis/education tool, not a trading bot, and
nothing here is investment advice.
