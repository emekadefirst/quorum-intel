"""Load and validate raw OHLC data."""

from __future__ import annotations

import pandas as pd

OHLC = ["open", "high", "low", "close"]


def _standardise(df: pd.DataFrame, time_col: str | None = None) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    if time_col:
        df = df.set_index(time_col.lower())
    elif not isinstance(df.index, pd.DatetimeIndex):
        for cand in ("time", "timestamp", "datetime", "date", "gmt time"):
            if cand in df.columns:
                df = df.set_index(cand)
                break
    df.index = pd.to_datetime(df.index, utc=True, errors="coerce")
    df = df[~df.index.isna()].sort_index()
    df = df[~df.index.duplicated(keep="last")]

    missing = [c for c in OHLC if c not in df.columns]
    if missing:
        if "close" in df.columns:  # close-only series: synthesise flat candles
            for c in missing:
                df[c] = df["close"]
        else:
            raise ValueError(f"Missing columns {missing}; got {list(df.columns)}")

    keep = OHLC + (["volume"] if "volume" in df.columns else [])
    df = df[keep].astype(float).dropna(subset=OHLC)
    # drop impossible candles
    bad = (df.high < df.low) | (df.close <= 0)
    return df[~bad]


def load_csv(path: str, time_col: str | None = None) -> pd.DataFrame:
    """CSV with a time column plus open/high/low/close (volume optional)."""
    return _standardise(pd.read_csv(path), time_col)


def fetch_yfinance(
    symbol: str = "GBPUSD=X", interval: str = "1h", period: str = "2y"
) -> pd.DataFrame:
    """Quick public data for prototyping. Note: Yahoo caps 1h history at ~730 days."""
    import yfinance as yf  # optional dependency

    raw = yf.download(
        symbol, interval=interval, period=period, auto_adjust=False, progress=False
    )
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    return _standardise(raw.reset_index())


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in df.columns:
        agg["volume"] = "sum"
    return df.resample(rule).agg(agg).dropna(subset=["close"])


def bars_per_day(df: pd.DataFrame) -> float:
    step = df.index.to_series().diff().median()
    return (
        float(pd.Timedelta("1D") / step)
        if pd.notna(step) and step > pd.Timedelta(0)
        else 1.0
    )
