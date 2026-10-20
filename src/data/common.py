"""Shared helpers: canonical OHLC format that src/quant/data.py expects."""

from __future__ import annotations

import pandas as pd

OHLC = ["open", "high", "low", "close"]

# Canonical pair -> (dukascopy, oanda, deriv) symbols
PAIRS: dict[str, tuple[str, str, str]] = {
    "GBPUSD": ("GBP/USD", "GBP_USD", "frxGBPUSD"),
    "EURUSD": ("EUR/USD", "EUR_USD", "frxEURUSD"),
    "USDJPY": ("USD/JPY", "USD_JPY", "frxUSDJPY"),
}


def to_canonical(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise column names, enforce UTC DatetimeIndex, drop bad rows."""
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    if not isinstance(out.index, pd.DatetimeIndex):
        for cand in ("time", "timestamp", "datetime", "date"):
            if cand in out.columns:
                out = out.set_index(cand)
                break
    out.index = pd.to_datetime(out.index, utc=True, errors="coerce")
    out = out.loc[out.index.notna()].sort_index()
    out = out.loc[~out.index.duplicated(keep="last")]

    missing = [c for c in OHLC if c not in out.columns]
    if missing:
        raise ValueError(f"Missing OHLC columns {missing}; got {list(out.columns)}")

    keep = OHLC + (["volume"] if "volume" in out.columns else [])
    out = out[keep].astype(float).dropna(subset=list(OHLC))
    bad = (out["high"] < out["low"]) | (out["close"] <= 0)
    return out.loc[~bad]
