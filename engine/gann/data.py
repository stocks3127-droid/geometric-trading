"""Market data access for NSE (India) — unified OHLCV loader.

Three sources, tried in order (``source="auto"``):

1. **yfinance**  — intraday (1m/2m/5m/15m/30m/60m, up to 60 days) and
   daily history for any NSE symbol via the ``SYMBOL.NS`` suffix.
   ``pip install yfinance``
2. **jugaad-data** — free NSE EOD history (Rule 10's daily/weekly/monthly
   requirements) straight from NSE.  ``pip install jugaad-data``
   https://github.com/jugaad-py/jugaad-data
3. **synthetic** — deterministic offline generator so the engine, its
   tests and the demo always work without a network.

Returns a tidy frame: DatetimeIndex (Asia/Kolkata for intraday) with
columns ``Open, High, Low, Close, Volume``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

__all__ = ["fetch", "fetch_yfinance", "fetch_jugaad", "synthetic"]

COLS = ["Open", "High", "Low", "Close", "Volume"]

NSE_INTRADAY_INTERVALS = {"1m": "7d", "2m": "60d", "5m": "60d", "15m": "60d", "30m": "60d", "60m": "730d", "90m": "60d"}


def _tidy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).capitalize() for c in df.columns]
    df = df[COLS].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


def fetch_yfinance(symbol: str, days: int = 60, interval: str = "5m") -> pd.DataFrame:
    """NSE intraday/daily candles from Yahoo Finance via ``SYMBOL.NS``."""
    import yfinance as yf  # lazy import

    period = NSE_INTRADAY_INTERVALS.get(interval)
    if interval == "1d":
        period = f"{max(days, 1) * 2}d"
    if period is None:
        raise ValueError(f"unsupported interval {interval!r}")
    if interval != "1d":
        # yfinance caps intraday history; clamp `days` to the allowed window
        cap = {"7d": 7, "60d": 60, "730d": 730}[period]
        days = min(days, cap)
    raw = yf.download(f"{symbol.upper()}.NS", interval=interval, period=period, progress=False, auto_adjust=False)
    if raw is None or raw.empty:
        raise RuntimeError(f"yfinance returned no data for {symbol}.NS")
    if isinstance(raw.columns, pd.MultiIndex):  # yfinance >= 0.2 single-ticker frames
        raw.columns = raw.columns.get_level_values(0)
    df = _tidy(raw)
    df = df.tail(days * (1 if interval == "1d" else 80))  # keep requested window
    return df


def fetch_jugaad(symbol: str, days: int = 365, interval: str = "1d") -> pd.DataFrame:
    """NSE **daily** history via jugaad-data (no API key, straight from NSE)."""
    if interval != "1d":
        raise ValueError("jugaad-data source supports daily (1d) bars only")
    from jugaad_data.nse import NSE  # lazy import

    to_d = date.today()
    from_d = to_d - timedelta(days=max(days, 5) * 2)
    df = NSE().historical_data(symbol.upper(), from_d, to_d, series="EQ")
    if df is None or df.empty:
        raise RuntimeError(f"jugaad-data returned no data for {symbol}")
    mapping = {c.upper(): c.capitalize() for c in df.columns}
    df = df.rename(columns=mapping)
    df.index = pd.to_datetime(df["Date"] if "Date" in df else df.index)
    df["Volume"] = df.get("Volume", pd.Series(np.zeros(len(df)), index=df.index))
    df = _tidy(df).tail(days)
    return df


def synthetic(
    symbol: str = "DEMO",
    days: int = 30,
    interval: str = "5m",
    seed: int = 42,
    start_price: float = 24_000.0,
    base_vol: float = 0.0012,
    drift: float = 0.00008,
) -> pd.DataFrame:
    """Deterministic synthetic OHLCV — offline demo & tests.

    Builds a Gann-friendly random walk: trending legs with retracements,
    NSE session timestamps (09:15–15:30 IST), weekends skipped.
    """
    rng = np.random.default_rng(seed)
    minutes = {"1m": 1, "2m": 2, "5m": 5, "15m": 15, "30m": 30, "60m": 60}[interval]
    bars_per_day = 375 // minutes
    n = days * bars_per_day

    # regime-switching drift so real swings (and 50% retracements) appear
    regime = np.zeros(n)
    i = 0
    while i < n:
        leg = int(rng.integers(bars_per_day, 3 * bars_per_day))
        regime[i : i + leg] = rng.choice([1.0, -1.0]) * rng.uniform(0.5, 1.6)
        i += leg
    rets = drift * regime + rng.normal(0.0, base_vol, n)
    close = start_price * np.exp(np.cumsum(rets))
    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1]
    spread = np.abs(rng.normal(0, base_vol * 0.6, n)) * close
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    vol = rng.integers(50_000, 500_000, n) * (1 + np.abs(rets) * 50)

    # NSE session timestamps, skipping weekends
    ts = []
    d = datetime(2026, 8, 3)  # a Monday
    while len(ts) < n:
        if d.weekday() < 5:
            day_bars = pd.date_range(
                f"{d.date()} 09:15", f"{d.date()} 15:29", freq=f"{minutes}min", tz="Asia/Kolkata"
            )[:bars_per_day]
            ts.extend(day_bars)
        d += timedelta(days=1)
    ts = pd.DatetimeIndex(ts[:n])

    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol.astype(float)},
        index=ts,
    )
    df.index.name = "Datetime"
    return df


def fetch(symbol: str, days: int = 60, interval: str = "5m", source: str = "auto") -> pd.DataFrame:
    """Load OHLCV for an NSE symbol.

    ``source``: ``auto`` | ``yfinance`` | ``jugaad`` | ``synthetic``.
    ``auto`` tries yfinance -> jugaad (daily only) -> synthetic with a
    warning, so the engine never hard-fails offline.
    """
    if source == "synthetic":
        return synthetic(symbol=symbol, days=days, interval=interval)
    if source == "yfinance":
        return fetch_yfinance(symbol, days, interval)
    if source == "jugaad":
        return fetch_jugaad(symbol, days, interval)
    if source == "auto":
        errors = []
        for attempt in ("yfinance", "jugaad"):
            try:
                if attempt == "jugaad" and interval != "1d":
                    continue
                return fetch_yfinance(symbol, days, interval) if attempt == "yfinance" \
                    else fetch_jugaad(symbol, days, interval)
            except Exception as e:  # pragma: no cover - network dependent
                errors.append(f"{attempt}: {e}")
        import warnings

        warnings.warn(
            f"live sources unavailable ({'; '.join(errors)}) — falling back to synthetic data",
            RuntimeWarning,
        )
        return synthetic(symbol=symbol, days=days, interval=interval)
    raise ValueError(f"unknown source {source!r}")
