#!/usr/bin/env bash
# Bootstrap the Gann engine environment.
#   ./setup.sh && .venv/bin/python -m gann demo
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -r requirements.txt

echo
echo "  installed.  try:"
echo "    source .venv/bin/activate"
echo "    python -m gann demo                        # offline synthetic demo"
echo "    python -m gann analyze RELIANCE --days 20  # live NSE 15m (needs yfinance)"
echo "    python -m gann sq9 496                     # rulebook Rule-134 example"
echo "    python -m gann timing 2026-08-01           # time cycles from a pivot"
echo "    pytest -q                                  # run the test suite"
