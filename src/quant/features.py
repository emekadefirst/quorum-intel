"""Indicators and model features. Everything here is causal: the value at bar t
uses only data up to and including bar t (tests/test_no_lookahead.py checks this)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift()
    return pd.concat(
        [df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1
    ).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1 / n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def macd(close: pd.Series, fast=12, slow=26, signal=9):
    line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig


def bollinger(close: pd.Series, n=20, k=2.0):
    ma = close.rolling(n).mean()
    sd = close.rolling(n).std()
    upper, lower = ma + k * sd, ma - k * sd
    pctb = (close - lower) / (upper - lower).replace(0, np.nan)
    bandwidth = (upper - lower) / ma
    return pctb, bandwidth


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up, dn = df["high"].diff(), -df["low"].diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr_s = true_range(df).ewm(alpha=1 / n, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / n, adjust=False).mean() / tr_s
    minus_di = 100 * minus_dm.ewm(alpha=1 / n, adjust=False).mean() / tr_s
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"]
    a = atr(df, 14)
    logc = np.log(c)
    r1 = logc.diff()
    f = pd.DataFrame(index=df.index)

    for k in (1, 3, 6, 12, 24, 48):
        f[f"ret_{k}"] = logc.diff(k)

    f["rsi14"] = rsi(c, 14)
    _, _, hist = macd(c)
    f["macd_hist_atr"] = hist / a
    f["pctb"], f["bb_width"] = bollinger(c)
    f["adx14"] = adx(df, 14)
    for n in (20, 50, 200):
        f[f"dist_sma{n}_atr"] = (c - c.rolling(n).mean()) / a

    f["atr_pct"] = a / c
    f["rv20"] = r1.rolling(20).std()
    f["rv100"] = r1.rolling(100).std()
    f["vol_ratio"] = f["rv20"] / f["rv100"]

    hi, lo = df["high"].rolling(24).max(), df["low"].rolling(24).min()
    f["range_pos24"] = (c - lo) / (hi - lo).replace(0, np.nan)

    rng = (df["high"] - df["low"]).replace(0, np.nan)
    f["body_ratio"] = (df["close"] - df["open"]) / rng
    f["upper_wick"] = (df["high"] - df[["open", "close"]].max(axis=1)) / rng
    f["lower_wick"] = (df[["open", "close"]].min(axis=1) - df["low"]) / rng

    # calendar features only make sense intraday
    step = df.index.to_series().diff().median()
    if pd.notna(step) and step < pd.Timedelta("20h"):
        hour = df.index.hour + df.index.minute / 60
        f["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        f["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    dow = df.index.dayofweek
    f["dow_sin"] = np.sin(2 * np.pi * dow / 5)
    f["dow_cos"] = np.cos(2 * np.pi * dow / 5)

    return f.replace([np.inf, -np.inf], np.nan)
