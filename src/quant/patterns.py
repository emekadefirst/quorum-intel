"""Pattern discovery with the matrix profile (stumpy).

similar_setups: "find past moments that looked like now" and report what happened next.
novelty: how unusual is the current shape versus everything seen before.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def similar_setups(close: pd.Series, window: int = 48, horizon: int = 12, top_k: int = 30) -> dict:
    import stumpy

    T = np.log(close.to_numpy(dtype="float64"))
    n = len(T)
    if n < window * 4 + horizon:
        return {"available": False, "reason": "not enough history"}

    query = T[-window:]
    dp = stumpy.mass(query, T)  # z-normalised distance profile, length n-window+1
    dp = np.where(np.isfinite(dp), dp, np.inf)

    # a match starting at i ends at e=i+window-1 and needs its outcome e+horizon observed,
    # and must not overlap the query window itself.
    last_start = min(n - window - horizon, n - 2 * window)
    dp[last_start + 1 :] = np.inf

    picked: list[int] = []
    for i in np.argsort(dp):
        if not np.isfinite(dp[i]):
            break
        if all(abs(i - j) >= window for j in picked):  # de-duplicate neighbouring matches
            picked.append(int(i))
        if len(picked) >= top_k:
            break
    if len(picked) < 5:
        return {"available": False, "reason": "too few distinct matches"}

    ends = np.array(picked) + window - 1
    fwd = T[ends + horizon] - T[ends]  # log return after each match
    dists = dp[picked]
    bps = fwd * 1e4
    return {
        "available": True,
        "window_bars": window,
        "horizon_bars": horizon,
        "n_matches": len(picked),
        "mean_match_distance": round(float(dists.mean()), 3),
        "max_possible_distance": round(float(2 * np.sqrt(window)), 3),
        "hit_rate_up": round(float((fwd > 0).mean()), 3),
        "hit_rate_stderr": round(float(np.sqrt(0.25 / len(picked))), 3),  # ~±0.09 at 30 matches: treat extremes as noise
        "mean_fwd_return_bps": round(float(bps.mean()), 2),
        "median_fwd_return_bps": round(float(np.median(bps)), 2),
        "fwd_return_p25_p75_bps": [round(float(np.percentile(bps, 25)), 2), round(float(np.percentile(bps, 75)), 2)],
        "best_match_times": [close.index[e].isoformat() for e in ends[:3]],
    }


def novelty(close: pd.Series, window: int = 48, max_bars: int = 10000) -> dict:
    """Percentile of the latest window's nearest-neighbour distance against the whole
    matrix profile. High = shape rarely/never seen before (patterns may not transfer)."""
    import stumpy

    s = close.iloc[-max_bars:]
    T = np.log(s.to_numpy(dtype="float64"))
    if len(T) < window * 4:
        return {"available": False}
    mp = stumpy.stump(T, m=window)
    d = mp[:, 0].astype(float)
    ok = np.isfinite(d)
    latest = d[-1]
    pct = float((d[ok] < latest).mean() * 100) if np.isfinite(latest) else float("nan")
    i = int(np.nanargmin(np.where(ok, d, np.inf)))
    j = int(mp[i, 1])
    return {
        "available": True,
        "latest_window_novelty_percentile": None if np.isnan(pct) else round(pct, 1),
        "strongest_motif_pair": [s.index[i].isoformat(), s.index[j].isoformat()],
        "strongest_motif_distance": round(float(d[i]), 3),
    }
