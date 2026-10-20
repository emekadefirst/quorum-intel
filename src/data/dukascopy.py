"""Historical FX data from Dukascopy (free, no API key, back to ~2003).

Uses the `dukascopy-python` package which already handles .bi5 decoding and
resumable downloads. Follow Dukascopy's data usage agreement.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.configs.data import DATA_CACHE_DIR
from src.data.common import PAIRS, to_canonical

# dukascopy-python's own granularity constants
_INTERVAL_MAP = {
    "tick": "TICK",
    "1m": "MIN_1",
    "5m": "MIN_5",
    "15m": "MIN_15",
    "30m": "MIN_30",
    "1h": "HOUR_1",
    "4h": "HOUR_4",
    "1d": "DAY_1",
    "1w": "WEEK_1",
    "1mo": "MONTH_1",
}


def _as_utc(value: datetime | str) -> pd.Timestamp:
    """Accept naive or tz-aware datetime/str; always return a UTC Timestamp."""
    ts = pd.Timestamp(value)
    out = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    return out  # type: ignore[return-value]


def _cache_path(pair: str, interval: str, start: datetime, end: datetime) -> Path:
    cache = Path(DATA_CACHE_DIR) / "dukascopy"
    cache.mkdir(parents=True, exist_ok=True)
    name = f"{pair}_{interval}_{start:%Y%m%d}_{end:%Y%m%d}.parquet"
    return cache / name


def fetch_dukascopy(
    pair: str = "GBPUSD",
    start: datetime | str = "2003-05-05",
    end: datetime | str | None = None,
    interval: str = "1h",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch historical OHLC bars from Dukascopy.

    Returns a canonical UTC-indexed DataFrame with open/high/low/close (+ volume).
    """
    if pair not in PAIRS:
        raise ValueError(f"Unknown pair {pair}; known: {list(PAIRS)}")
    if interval not in _INTERVAL_MAP:
        raise ValueError(f"Unknown interval {interval}; known: {list(_INTERVAL_MAP)}")

    start_ts = _as_utc(start)
    end_ts = _as_utc(end) if end else pd.Timestamp.now(tz="UTC")
    if pd.isna(start_ts) or pd.isna(end_ts):
        raise ValueError(f"Invalid start/end: {start!r} / {end!r}")
    start_dt: datetime = start_ts.to_pydatetime()  # type: ignore[assignment]
    end_dt: datetime = end_ts.to_pydatetime()  # type: ignore[assignment]

    path = _cache_path(pair, interval, start_dt, end_dt)
    if use_cache and path.exists():
        return to_canonical(pd.read_parquet(path))

    try:
        import dukascopy_python  # type: ignore[import-not-found]
        import dukascopy_python.instruments as _instruments  # type: ignore[import-not-found]
    except ImportError as e:
        raise ImportError(
            "dukascopy-python not installed. Run: uv add dukascopy-python"
        ) from e

    # per-pair instrument constants, fall back to GBPUSD if the pair isn't a major
    instrument = getattr(
        _instruments,
        f"INSTRUMENT_FX_MAJORS_{pair[:3]}_{pair[3:]}",
        _instruments.INSTRUMENT_FX_MAJORS_GBP_USD,
    )
    interval_const = getattr(dukascopy_python, f"INTERVAL_{_INTERVAL_MAP[interval]}")
    offer_side = dukascopy_python.OFFER_SIDE_BID

    df = dukascopy_python.fetch(
        instrument=instrument,
        interval=interval_const,
        offer_side=offer_side,
        start=start_dt,
        end=end_dt,
    )  # type: ignore[no-untyped-call]
    df = to_canonical(df)

    if use_cache and not df.empty:
        df.to_parquet(path)
    return df
