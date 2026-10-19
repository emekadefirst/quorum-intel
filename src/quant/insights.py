"""Assemble every analysis into one JSON-serialisable dict for the LLM layer."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from src.quant.data import bars_per_day
from src.quant.features import build_features
from src.quant.levels import key_levels
from src.quant.model import run_model
from src.quant.patterns import novelty, similar_setups
from src.quant.regime import classify_regime, garch_forecast


@dataclass
class Config:
    pair: str = "GBPUSD"
    timeframe: str = "1h"  # label only; bar spacing is detected from the data
    horizon: int = 12  # bars ahead to predict
    window: int = 48  # bars per pattern window
    top_k: int = 30  # similar setups to keep
    cost_bps: float = 1.0  # assumed round-trip cost in basis points
    conf_thr: float = 0.55
    n_folds: int = 6
    novelty: bool = True
    max_bars_novelty: int = 10000


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if (math.isnan(o) or math.isinf(o)) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    return o


def _snapshot(df: pd.DataFrame) -> dict:
    f = build_features(df).iloc[-1]
    rsi = float(f["rsi14"])
    pctb = float(f["pctb"])
    bpd = bars_per_day(df)
    day_bars = max(1, int(round(bpd)))
    c = df["close"]
    return {
        "price": round(float(c.iloc[-1]), 5),
        "change_1d_pct": round(float((c.iloc[-1] / c.iloc[-1 - day_bars] - 1) * 100), 3)
        if len(c) > day_bars
        else None,
        "change_5d_pct": round(
            float((c.iloc[-1] / c.iloc[-1 - 5 * day_bars] - 1) * 100), 3
        )
        if len(c) > 5 * day_bars
        else None,
        "rsi14": round(rsi, 1),
        "rsi_state": "overbought"
        if rsi >= 70
        else "oversold"
        if rsi <= 30
        else "neutral",
        "bollinger_pctb": round(pctb, 2),
        "bollinger_state": "above_upper"
        if pctb > 1
        else "below_lower"
        if pctb < 0
        else "inside_bands",
        "macd_hist_in_atr": round(float(f["macd_hist_atr"]), 3),
        "dist_from_sma50_atr": round(float(f["dist_sma50_atr"]), 2),
        "dist_from_sma200_atr": None
        if np.isnan(f["dist_sma200_atr"])
        else round(float(f["dist_sma200_atr"]), 2),
    }


def build_insights(df: pd.DataFrame, cfg: Config | None = None) -> dict:
    cfg = cfg or Config()
    close = df["close"]

    vol = garch_forecast(close, cfg.horizon)
    if vol:
        px = float(close.iloc[-1])
        s = vol["horizon_vol_pct"] / 100
        vol["one_sigma_price_range_over_horizon"] = [
            round(px * math.exp(-s), 5),
            round(px * math.exp(s), 5),
        ]

    out = {
        "meta": {
            "pair": cfg.pair,
            "timeframe": cfg.timeframe,
            "as_of": df.index[-1].isoformat(),
            "bars_used": int(len(df)),
            "history_start": df.index[0].isoformat(),
            "config": asdict(cfg),
        },
        "snapshot": _snapshot(df),
        "regime": classify_regime(df),
        "volatility_forecast": vol,
        "levels": key_levels(df),
        "similar_setups": similar_setups(close, cfg.window, cfg.horizon, cfg.top_k),
        "novelty": novelty(close, cfg.window, cfg.max_bars_novelty)
        if cfg.novelty
        else {"available": False},
        "model": run_model(
            df, cfg.horizon, cfg.n_folds, conf_thr=cfg.conf_thr, cost_bps=cfg.cost_bps
        ),
        "reading_guide": [
            "model.signal_quality is the honest summary of out-of-sample edge; 'no_edge_detected' means treat p_up as noise.",
            "similar_setups are historical analogues, not forecasts; check n_matches and novelty before leaning on them.",
            "volatility_forecast is generally more reliable than direction; use it for sizing and stop distance.",
            "Nothing here accounts for scheduled news or geopolitical events; that context comes from the news layer.",
        ],
    }
    return _clean(out)


def to_json(insights: dict, indent: int = 2) -> str:
    return json.dumps(insights, indent=indent)
