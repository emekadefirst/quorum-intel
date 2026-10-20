"""Signals service: fetch OHLC + run quant insights with a short TTL cache.

Uses Dukascopy via src.data (free, no API key) rather than yfinance which
gets rate-limited by Yahoo. One in-memory dict keyed by (pair, interval),
TTL in seconds. Good enough for a single-process dev server.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from src.data.pipeline import fetch_history
from src.quant.insights import Config, build_insights

_CACHE: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
_TTL = 300  # 5 minutes

# How much history to pull per interval. Enough bars for the model (~2000+)
# and GARCH (~500+) without downloading 20 years every time.
# Keep lookbacks modest: Dukascopy downloads bar-by-bar on first run.
# After the first fetch, results are cached to parquet (daily key).
_LOOKBACK_DAYS = {
    "1m": 3,
    "5m": 14,
    "15m": 30,
    "30m": 60,
    "1h": 90,
    "4h": 180,
    "1d": 1000,
}


class SignalsService:
    @classmethod
    def get_current(
        cls, pair: str = "GBPUSD", interval: str = "1h"
    ) -> dict[str, Any]:
        key = (pair, interval)
        now = time.monotonic()
        hit = _CACHE.get(key)
        if hit and now - hit[0] < _TTL:
            return hit[1]

        lookback = _LOOKBACK_DAYS.get(interval, 180)
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback)

        df = fetch_history(pair=pair, start=start, end=end, interval=interval)
        if df.empty:
            raise RuntimeError(
                f"No OHLC data returned for {pair} {interval} "
                f"({start:%Y-%m-%d} -> {end:%Y-%m-%d}). "
                "Check Dukascopy connectivity or try a shorter interval."
            )

        insights = build_insights(df, Config(pair=pair, timeframe=interval))
        _CACHE[key] = (now, insights)
        return insights
