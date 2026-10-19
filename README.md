# gbpusd_quant — quant layer

Raw OHLC in, one structured JSON "insight" object out. Built to feed an LLM layer
(news + reasoning + decisions), which should treat this as evidence, not as orders.

## Run
    pip install -r requirements.txt
    python -m quant_layer --csv gbpusd_1h.csv --timeframe 1h --out insights.json
    python -m quant_layer --yfinance --interval 1h          # quick prototyping data
    python -m quant_layer --csv ticks_or_1m.csv --resample 1h

CSV needs a time column (time/timestamp/datetime/date) plus open, high, low, close.

## From Python (what the agent layer will call)
    from quant_layer import Config, build_insights
    from quant_layer.data import load_csv
    insights = build_insights(load_csv("gbpusd_1h.csv"), Config(horizon=12, cost_bps=1.0))

## Modules
| file | what it does |
|---|---|
| data.py | load/validate CSV or Yahoo data, resample |
| features.py | RSI, MACD, Bollinger, ATR, ADX, returns, candle shape, calendar (causal) |
| regime.py | GARCH(1,1)-t vol forecast, trend/vol regime |
| patterns.py | stumpy: similar past setups + what followed, shape novelty, top motif |
| levels.py | support/resistance from confirmed swing pivots, in ATR distance |
| model.py | LightGBM P(up) with walk-forward + purge gap + cost-aware OOS stats |
| insights.py | assembles everything into one JSON dict |
| news/fetch.py | Scrapling AsyncFetcher: RSS/Atom feeds, optional article text (robots.txt + per-host delay) |
| news/relevance.py | transparent keyword topic tags + relevance score for GBP/USD |
| news/digest.py | dedupe, recency decay, source health -> news digest JSON |
| news/sources.json | feed list: edit freely, verify URLs |
| intelligence.py | quant insights + news digest in one payload for the LLM |

## News layer (Scrapling)
    pip install -r requirements.txt            # installs scrapling[fetchers]; no browser download needed for HTTP/RSS
    python -m quant_layer.news --hours 48 --excerpts 3 --out news.json
    python -m quant_layer --csv gbpusd_1h.csv --with-news --out intelligence.json

    from quant_layer.intelligence import build_intelligence
    intel = build_intelligence(df, Config(), news={"lookback_hours": 24, "max_items": 20})

- Uses `AsyncFetcher.get` for feeds (concurrent, retries, timeouts). Feeds are parsed with defusedxml.
- `source_health` reports every failed feed, so the LLM can say "BoE feed was down" instead of assuming no news.
- Article text is fetched only for the top N items, only if robots.txt allows, and is truncated.
- Only headline, short summary, link and a short excerpt are kept. Fetch what the site's terms allow.
- Scrapling's stealth/browser fetchers (`StealthyFetcher`, `DynamicFetcher`) exist but are NOT used: official feeds
  don't need them, and bypassing a site's protections is a terms-of-use decision for you to make deliberately.
- All fetched text is flagged UNTRUSTED in `reading_guide`. Your agent prompt must repeat this
  (prompt injection via headlines is a real risk once the agent can place trades).
- Not included: an economic calendar (scheduled CPI/payroll/rate dates). Add one source for that next.

## Output sections
meta, snapshot, regime, volatility_forecast, levels, similar_setups, novelty, model, reading_guide.
Key field: `model.signal_quality` in {no_edge_detected, weak, modest}. It is never "strong" by design.

## Honesty built in
- Walk-forward only, with a purge gap of `horizon` bars between train and test.
- OOS accuracy and trade stats use non-overlapping samples and report a z-score / stderr.
- Costs are subtracted (`cost_bps`, default 1.0 bps round trip; set it to your broker's real spread).
- `tests/test_no_lookahead.py` verifies features at bar t don't change when future bars are removed.
- On pure random-walk data it reports no_edge_detected; sanity check your own data the same way.

## Known limits
- Daily bars: raise `--horizon` sensibly (e.g. 5) and use `--window 30`.
- Novelty (matrix profile) is O(n^2); capped at last 10,000 bars, or `--no-novelty` to skip.
- Similar-setup stats on ~30 matches are noisy (see hit_rate_stderr).
- No news/fundamentals here; that is the next layer.
