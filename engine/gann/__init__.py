"""Gann geometric trading engine — companion code for the
*Gann Market Geometry Rulebook* (Parts 1 & 2).

Modules
-------
angles           Module 04 (Rules 24–42): geometric angle family & fans
square_of_nine   Modules 10–11 (Rules 115, 130–139): SQ9/SQ4 wheels
levels           Module 08 (Rules 82–94): range divisions & 50% king
timing           Modules 07/12 (Rules 135–139, 171): time cycles
swings           Modules 03/14: zigzag pivots & trend calls
data             NSE data: yfinance / jugaad-data / synthetic offline
chart            Module 02 (Rules 05–10): Gann-scaled charts
analysis         full pre-trade workup tying it all together
"""

__version__ = "0.1.0"

from . import angles, levels, square_of_nine, swings, timing  # noqa: F401
