"""OANDA v20 REST + streaming for live/recent FX data.

Candles cap at ~5000 bars per request, so we paginate. Create a free practice
account at https://developer.oanda.com and set OANDA_API_TOKEN in .env.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import httpx
import pandas as pd

from src.configs.data import OANDA_API_TOKEN, OANDA_BASE_URL, OANDA_STREAM_URL
from src.data.common import PAIRS, to_canonical

_GRANULARITY = {
    "5s": "S5", "10s": "S10", "15s": "S15", "30s": "S30",
    "1m": "M1", "5m": "M5", "15m": "M15", "30m": "M30",
    "1h": "H1", "4h": "H4", "1d": "D", "1w": "W", "1mo": "M",
}
_MAX_COUNT = 5000


def _headers() -> dict[str, str]:
    if not OANDA_API_TOKEN:
        raise RuntimeError("OANDA_API_TOKEN not set in environment")
    return {
        "Authorization": f"Bearer {OANDA_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _instrument(pair: str) -> str:
    if pair not in PAIRS:
        raise ValueError(f"Unknown pair {pair}; known: {list(PAIRS)}")
    return PAIRS[pair][1]


def _candles_to_df(candles: list[dict]) -> pd.DataFrame:
    rows = []
    for c in candles:
        if not c.get("complete"):
            continue
        mid = c.get("mid") or c.get("bid") or c.get("ask")
        if not mid:
            continue
        rows.append({
            "time": c["time"],
            "open": mid["o"],
            "high": mid["h"],
            "low": mid["l"],
            "close": mid["c"],
            "volume": c.get("volume", 0),
        })
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(rows).set_index("time")
    return to_canonical(df)


def fetch_oanda(
    pair: str = "GBPUSD",
    interval: str = "1h",
    count: int = 500,
    start: datetime | str | None = None,
    end: datetime | str | None = None,
    price: str = "M",  # M=mid, B=bid, A=ask
) -> pd.DataFrame:
    """Fetch recent OHLC candles from OANDA. Paginates automatically when
    using start/end for multi-request pulls."""
    if interval not in _GRANULARITY:
        raise ValueError(f"Unknown interval {interval}; known: {list(_GRANULARITY)}")

    gran = _GRANULARITY[interval]
    url = f"{OANDA_BASE_URL}/v3/instruments/{_instrument(pair)}/candles"
    base_params = {"granularity": gran, "price": price}

    with httpx.Client(headers=_headers(), timeout=30) as client:
        if start is None and end is None:
            # single request, latest N bars
            params = {**base_params, "count": min(count, _MAX_COUNT)}
            r = client.get(url, params=params)
            r.raise_for_status()
            return _candles_to_df(r.json().get("candles", []))

        # paginated range request
        frames: list[pd.DataFrame] = []
        cursor = pd.Timestamp(start, tz="UTC") if start else None
        end_ts = pd.Timestamp(end, tz="UTC") if end else pd.Timestamp.now(tz="UTC")
        while True:
            params = {**base_params, "count": _MAX_COUNT}
            if cursor is not None:
                params["from"] = cursor.isoformat().replace("+00:00", "Z")
            r = client.get(url, params=params)
            r.raise_for_status()
            candles = r.json().get("candles", [])
            if not candles:
                break
            df = _candles_to_df(candles)
            if df.empty:
                break
            frames.append(df)
            last = df.index[-1]
            if last >= end_ts or len(candles) < _MAX_COUNT:
                break
            cursor = last + pd.Timedelta(seconds=1)

    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    out = pd.concat(frames)
    out = out.loc[~out.index.duplicated(keep="last")].sort_index()
    if end:
        out = out.loc[out.index <= pd.Timestamp(end, tz="UTC")]
    return out


async def stream_oanda_prices(
    account_id: str,
    pairs: list[str] | None = None,
) -> AsyncIterator[dict]:
    """Yield live price ticks for the given pairs. Yields {time, pair, bid, ask}.

    Heartbeats are filtered out. The caller controls the loop.
    """
    pairs = pairs or ["GBPUSD"]
    instruments = ",".join(_instrument(p) for p in pairs)
    url = f"{OANDA_STREAM_URL}/v3/accounts/{account_id}/pricing/stream"
    params = {"instruments": instruments}

    async with httpx.AsyncClient(headers=_headers(), timeout=None) as client:
        async with client.stream("GET", url, params=params) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") != "PRICE":
                    continue  # skip HEARTBEAT
                bids = msg.get("bids") or [{}]
                asks = msg.get("asks") or [{}]
                yield {
                    "time": datetime.fromisoformat(
                        msg["time"].replace("Z", "+00:00")
                    ).astimezone(timezone.utc),
                    "pair": msg["instrument"].replace("_", ""),
                    "bid": float(bids[0].get("price", 0)) or None,
                    "ask": float(asks[0].get("price", 0)) or None,
                }
