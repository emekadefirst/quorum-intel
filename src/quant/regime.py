"""Volatility forecast (GARCH) and market regime classification."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .features import adx


def garch_forecast(close: pd.Series, horizon: int, max_obs: int = 5000) -> dict | None:
    """GARCH(1,1)-t forecast of return volatility over `horizon` bars."""
    try:
        from arch import arch_model
    except ImportError:
        return None
    r = (
        (np.log(close).diff().dropna().iloc[-max_obs:]) * 1e4
    )  # basis points keeps the optimiser well scaled
    if len(r) < 500:
        return None
    try:
        res = arch_model(
            r, mean="Zero", vol="GARCH", p=1, q=1, dist="t", rescale=False
        ).fit(disp="off")
        var = res.forecast(horizon=horizon).variance.iloc[-1].to_numpy()
        p = res.params
        return {
            "next_bar_vol_pct": round(float(np.sqrt(var[0])) / 100, 4),
            "horizon_vol_pct": round(float(np.sqrt(var.sum())) / 100, 4),
            "persistence": float(p.get("alpha[1]", np.nan) + p.get("beta[1]", np.nan)),
            "converged": bool(res.convergence_flag == 0),
        }
    except Exception:  # noqa: BLE001 - GARCH can fail on odd data; degrade gracefully
        return None


def classify_regime(df: pd.DataFrame, lookback: int = 500) -> dict:
    c = df["close"]
    r = np.log(c).diff()
    rv = r.rolling(20).std()
    hist = rv.dropna().iloc[-lookback:]
    pct = float((hist < rv.iloc[-1]).mean() * 100) if len(hist) > 50 else float("nan")

    if np.isnan(pct):
        vol_state = "unknown"
    elif pct >= 90:
        vol_state = "extreme"
    elif pct >= 75:
        vol_state = "high"
    elif pct <= 25:
        vol_state = "low"
    else:
        vol_state = "normal"

    sma20, sma50 = c.rolling(20).mean().iloc[-1], c.rolling(50).mean().iloc[-1]
    a = float(adx(df).iloc[-1])
    if a >= 25 and sma20 > sma50:
        trend = "uptrend"
    elif a >= 25 and sma20 < sma50:
        trend = "downtrend"
    else:
        trend = "range"

    return {
        "trend": trend,
        "adx14": round(a, 1),
        "vol_state": vol_state,
        "realized_vol_percentile": None if np.isnan(pct) else round(pct, 1),
    }
