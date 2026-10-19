import argparse

from src.quant.data import fetch_yfinance, load_csv, resample_ohlc
from src.quant.insights import Config, build_insights, to_json


def run_quant():
    p = argparse.ArgumentParser(description="Quant layer: raw OHLC -> JSON insights")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="CSV with time + open/high/low/close")
    src.add_argument(
        "--yfinance",
        action="store_true",
        help="fetch GBPUSD=X from Yahoo (prototyping)",
    )
    p.add_argument("--time-col", default=None)
    p.add_argument("--resample", default=None, help="e.g. 1h, 4h, 1D")
    p.add_argument("--timeframe", default="1h", help="label for the output")
    p.add_argument("--interval", default="1h", help="yfinance interval")
    p.add_argument("--horizon", type=int, default=12)
    p.add_argument("--window", type=int, default=48)
    p.add_argument("--cost-bps", type=float, default=1.0)
    p.add_argument(
        "--no-novelty", action="store_true", help="skip matrix-profile novelty (faster)"
    )
    p.add_argument(
        "--with-news",
        action="store_true",
        help="also fetch the news digest (Scrapling) and emit one combined intelligence JSON",
    )
    p.add_argument("--news-hours", type=float, default=48)
    p.add_argument("--out", default=None, help="write JSON here (default: stdout)")
    a = p.parse_args()

    df = load_csv(a.csv, a.time_col) if a.csv else fetch_yfinance(interval=a.interval)
    if a.resample:
        df = resample_ohlc(df, a.resample)
    cfg = Config(
        timeframe=a.timeframe,
        horizon=a.horizon,
        window=a.window,
        cost_bps=a.cost_bps,
        novelty=not a.no_novelty,
    )
    if a.with_news:
        from .intelligence import build_intelligence

        js = to_json(build_intelligence(df, cfg, news={"lookback_hours": a.news_hours}))
    else:
        js = to_json(build_insights(df, cfg))
    if a.out:
        open(a.out, "w").write(js)
        print(f"wrote {a.out}")
    else:
        print(js)
