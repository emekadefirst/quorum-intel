"""Unified data pipeline: one call, consistent OHLC output for src/quant.

- fetch_history: deep history (Dukascopy, back to ~2003)
- fetch_recent:  recent/live candles (OANDA, needs API token)

Both return the canonical pandas DataFrame src/quant/data.py expects:
UTC DatetimeIndex, columns open/high/low/close (+ volume when available).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.data.dukascopy import fetch_dukascopy
from src.data.oanda import fetch_oanda


def fetch_history(
    pair: str = "GBPUSD",
    start: datetime | str = "2003-05-05",
    end: datetime | str | None = None,
    interval: str = "1h",
) -> pd.DataFrame:
    """Deep historical OHLC from Dukascopy. Cached to disk after first pull."""
    return fetch_dukascopy(pair=pair, start=start, end=end, interval=interval)


def fetch_recent(
    pair: str = "GBPUSD",
    interval: str = "1h",
    count: int = 500,
) -> pd.DataFrame:
    """Recent OHLC from OANDA (practice/live account)."""
    return fetch_oanda(pair=pair, interval=interval, count=count)
