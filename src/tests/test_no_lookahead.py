import numpy as np
import pandas as pd

from quant_layer.features import build_features


def synthetic(n=3000, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-02", periods=n, freq="1h", tz="UTC")
    ret = rng.standard_normal(n) * 0.0006
    close = 1.25 * np.exp(np.cumsum(ret))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.standard_normal(n)) * 0.0004
    return pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + spread,
                         "low": np.minimum(open_, close) - spread, "close": close}, index=idx)


def test_features_are_causal():
    df = synthetic()
    full = build_features(df)
    t = 2000
    part = build_features(df.iloc[: t + 1])
    pd.testing.assert_series_equal(full.iloc[t], part.iloc[t], check_names=False, rtol=1e-9, atol=1e-12)
