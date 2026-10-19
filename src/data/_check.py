"""One runnable check for the data pipeline.

Usage:
    uv run python -m src.data._check

Dukascopy pull can take ~30s for 1 week of 1h bars on first run (cached after).
OANDA check is skipped unless OANDA_API_TOKEN is set.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.data.common import OHLC
from src.data.pipeline import fetch_history, fetch_recent


def _assert_canonical(df, label: str) -> None:
    assert not df.empty, f"{label}: empty frame"
    assert all(c in df.columns for c in OHLC), f"{label}: missing OHLC columns"
    assert df.index.tz is not None, f"{label}: index not tz-aware"
    assert (df["high"] >= df["low"]).all(), f"{label}: high < low rows"
    print(f"{label}: {len(df)} bars, {df.index[0]} -> {df.index[-1]}")


def main() -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)

    print("[dukascopy] fetching 1 week of GBPUSD 1h bars...")
    hist = fetch_history("GBPUSD", start=start, end=end, interval="1h")
    _assert_canonical(hist, "dukascopy")

    try:
        print("[oanda] fetching last 100 GBPUSD 1h bars...")
        recent = fetch_recent("GBPUSD", interval="1h", count=100)
        _assert_canonical(recent, "oanda")
    except RuntimeError as e:
        print(f"[oanda] skipped: {e}")


if __name__ == "__main__":
    main()
