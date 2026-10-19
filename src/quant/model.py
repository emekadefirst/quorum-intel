"""Directional probability model with honest walk-forward validation.

- Expanding-window walk-forward, never a random split.
- A purge gap of `horizon` bars between train and test, because the label at bar t
  looks `horizon` bars ahead and would otherwise leak into the test fold.
- Trade statistics are computed on NON-overlapping bars (every `horizon`-th), since
  overlapping forward returns inflate apparent significance.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from .features import build_features


def _make_model():
    try:
        from lightgbm import LGBMClassifier

        return LGBMClassifier(
            n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=100,
            subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=5.0,
            verbose=-1, random_state=7,
        )
    except ImportError:
        from sklearn.ensemble import HistGradientBoostingClassifier

        return HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, l2_regularization=5.0, random_state=7)


def _quality(auc: float, z: float) -> str:
    if not np.isfinite(auc) or auc < 0.51 or z < 1.0:
        return "no_edge_detected"
    if auc < 0.53 or z < 2.0:
        return "weak"
    return "modest"  # deliberately never "strong" for FX


def run_model(df: pd.DataFrame, horizon: int = 12, n_folds: int = 6, min_train: int = 2000,
              conf_thr: float = 0.55, cost_bps: float = 1.0) -> dict:
    X_all = build_features(df)
    fwd = np.log(df["close"]).diff(horizon).shift(-horizon)  # return over next `horizon` bars
    y_all = (fwd > 0).astype(int)

    valid = X_all.notna().all(axis=1) & fwd.notna()
    X, y, f = X_all[valid], y_all[valid], fwd[valid]
    n = len(X)
    min_train = min(min_train, n // 2)
    if n < 600:
        return {"available": False, "reason": f"only {n} usable rows; need ~600+"}

    fold = (n - min_train) // n_folds
    proba = pd.Series(np.nan, index=X.index)
    for k in range(n_folds):
        s = min_train + k * fold
        e = n if k == n_folds - 1 else s + fold
        tr_end = s - horizon  # purge gap
        m = _make_model().fit(X.iloc[:tr_end], y.iloc[:tr_end])
        proba.iloc[s:e] = m.predict_proba(X.iloc[s:e])[:, 1]

    oos = proba.dropna()
    yo, fo = y.loc[oos.index], f.loc[oos.index]
    auc = float(roc_auc_score(yo, oos)) if yo.nunique() > 1 else float("nan")

    # non-overlapping subsample for honest accuracy / trade stats
    idx = np.arange(0, len(oos), horizon)
    po, yo_n, fo_n = oos.iloc[idx], yo.iloc[idx], fo.iloc[idx]
    base = float(yo_n.mean())
    pred_up = po > 0.5
    acc = float((pred_up == (yo_n == 1)).mean())
    z = (acc - 0.5) / np.sqrt(0.25 / max(len(po), 1))

    conf = ((po >= conf_thr) | (po <= 1 - conf_thr)).to_numpy()
    side = np.where(po.to_numpy() >= 0.5, 1.0, -1.0)
    gross_bps = side * fo_n.to_numpy() * 1e4
    net_bps = gross_bps - cost_bps
    k = int(conf.sum())
    trades = {
        "confidence_threshold": conf_thr,
        "n_trades": k,
        "hit_rate": round(float((gross_bps[conf] > 0).mean()), 3) if k else None,
        "avg_net_bps_per_trade": round(float(net_bps[conf].mean()), 2) if k else None,
        "avg_net_bps_stderr": round(float(net_bps[conf].std(ddof=1) / np.sqrt(k)), 2) if k > 1 else None,
        "cost_bps_assumed": cost_bps,
    }

    # final model on all labelled data, predict the latest bar
    final = _make_model().fit(X, y)
    latest_x = X_all.iloc[[-1]]
    p_up = float(final.predict_proba(latest_x)[:, 1][0]) if latest_x.notna().all(axis=1).iloc[0] else None

    imp = pd.Series(getattr(final, "feature_importances_", np.zeros(X.shape[1])), index=X.columns)
    imp = (imp / imp.sum()).sort_values(ascending=False).head(5) if imp.sum() > 0 else imp.head(5)

    return {
        "available": True,
        "horizon_bars": horizon,
        "p_up": None if p_up is None else round(p_up, 3),
        "oos": {
            "n_oos_bars": int(len(oos)),
            "n_independent_samples": int(len(po)),
            "base_rate_up": round(base, 3),
            "accuracy": round(acc, 3),
            "accuracy_z_vs_50pct": round(float(z), 2),
            "auc": round(auc, 3),
            "brier": round(float(brier_score_loss(yo, oos)), 4),
            "trades": trades,
        },
        "signal_quality": _quality(auc, float(z)),
        "top_features": {k: round(float(v), 3) for k, v in imp.items()},
    }
