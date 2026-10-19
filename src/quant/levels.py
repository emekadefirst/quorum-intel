"""Support/resistance from confirmed swing pivots, clustered by ATR distance."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from .features import atr


def key_levels(df: pd.DataFrame, order: int = 10, lookback: int = 2000,
               atr_mult: float = 0.5, per_side: int = 3) -> dict:
    d = df.iloc[-lookback:]
    n = len(d)
    if n < order * 4:
        return {"available": False}

    a = float(atr(df).iloc[-1])
    price = float(d["close"].iloc[-1])
    tol = a * atr_mult

    hi = argrelextrema(d["high"].to_numpy(), np.greater, order=order)[0]
    lo = argrelextrema(d["low"].to_numpy(), np.less, order=order)[0]
    # a pivot needs `order` bars after it to be confirmed
    hi, lo = hi[hi <= n - 1 - order], lo[lo <= n - 1 - order]

    pivots = [(float(d["high"].iloc[i]), d.index[i]) for i in hi] + \
             [(float(d["low"].iloc[i]), d.index[i]) for i in lo]
    if not pivots:
        return {"available": False}
    pivots.sort(key=lambda x: x[0])

    clusters, cur = [], [pivots[0]]
    for p in pivots[1:]:
        if p[0] - cur[-1][0] <= tol:
            cur.append(p)
        else:
            clusters.append(cur)
            cur = [p]
    clusters.append(cur)

    levels = [{
        "price": round(float(np.mean([p[0] for p in c])), 5),
        "touches": len(c),
        "last_touch": max(p[1] for p in c).isoformat(),
    } for c in clusters]

    def decorate(lv):
        lv["distance_atr"] = round(abs(lv["price"] - price) / a, 2)
        return lv

    below = sorted([decorate(l) for l in levels if l["price"] < price], key=lambda l: l["distance_atr"])
    above = sorted([decorate(l) for l in levels if l["price"] >= price], key=lambda l: l["distance_atr"])
    return {"available": True, "atr": round(a, 5), "support": below[:per_side], "resistance": above[:per_side]}
