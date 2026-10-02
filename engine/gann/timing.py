"""Time-factor tools — Rulebook Part 2, Module 12 (Rules 135, 138–139, 171)
with Part 1, Module 07 (Time > Price).

Rule 135: set the center to a major low/high date; probable trend-change
dates fall 45, 90, 120, 144, 180, 216, 270, 315, 360 calendar days out.
Rule 138 ranks the cycles: 90 (rank 1) > 45 > 180 > 135 > 270 > 120 > 315 >
225 > 144 > 216 (rank 10).
Rule 171: intraday, Gann circle numbers applied to minutes/hours from a
pivot give high-probability turning times.

The rulebook's Mar-21 example is astronomically anchored (equinox to
equinox); this engine uses plain calendar-day arithmetic per Rule 135.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

__all__ = ["calendar_cycles", "anniversary_dates", "intraday_cycles", "CYCLE_RANKS"]


CYCLE_DAYS: tuple[int, ...] = (45, 90, 120, 135, 144, 180, 216, 225, 270, 315, 360)

# Rule 138 importance ranking (1 = strongest).  The full 360° circle is not
# in the rulebook's top-10 list; it is the master cycle, so it gets rank 0.
CYCLE_RANKS: dict[int, int] = {
    360: 0,
    90: 1, 45: 2, 180: 3, 135: 4, 270: 5,
    120: 6, 315: 7, 225: 8, 144: 9, 216: 10,
}


def calendar_cycles(start: date, horizon_days: int = 366) -> list[tuple[date, int, int]]:
    """Upcoming trend-change dates from a major pivot date (Rule 135).

    Returns ``(date, days, rank)`` sorted by date, keeping only dates inside
    the horizon.  Rank is the Rule 138 importance ranking (1 = strongest).
    """
    out = []
    for d in CYCLE_DAYS:
        tgt = start + timedelta(days=d)
        if tgt <= date.today() or (tgt - date.today()).days > horizon_days:
            continue
        out.append((tgt, d, CYCLE_RANKS.get(d, 99)))
    out.sort(key=lambda t: t[0])
    return out


def anniversary_dates(start: date, years: int = 5) -> list[date]:
    """Rule 139: major yearly trends terminate on their anniversary dates."""
    today = date.today()
    y = today.year
    out = []
    for offset in range(years + 1):
        d = date(y + offset, start.month, start.day) if not (start.month == 2 and start.day == 29) \
            else date(y + offset, 3, 1)
        if d >= today:
            out.append(d)
    return out


# NSE cash session (IST)
NSE_OPEN = (9, 15)
NSE_CLOSE = (15, 30)


def intraday_cycles(pivot: datetime) -> list[tuple[datetime, int, int]]:
    """Rule 171 flavour: minute counts from an intraday pivot.

    45 / 90 / 120 / 144 / 180 / 225 / 270 / 315 / 360 minutes after the
    pivot (e.g. the 09:15 open or an intraday swing high/low) are natural
    Gann-circle turning times within the session.
    """
    out = []
    for m in CYCLE_DAYS:
        tgt = pivot + timedelta(minutes=m)
        if tgt.time() > datetime(2000, 1, 1, *NSE_CLOSE).time():
            continue  # beyond the session
        out.append((tgt, m, CYCLE_RANKS.get(m, 99)))
    out.sort(key=lambda t: t[0])
    return out
