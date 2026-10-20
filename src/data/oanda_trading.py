"""OANDA v20 trading operations: account, positions, orders, close/cancel.

Separate from oanda.py (which is read-only candles/streaming) because trading
operations have different concerns: auth, retries, idempotency, safety caps.

All operations go through the configured OANDA_ENV (practice by default).
Enforce OANDA_MAX_ORDER_UNITS as a hard safety cap on order size.
"""

from __future__ import annotations

from typing import Any, Literal

import httpx

from src.configs.data import (
    OANDA_ACCOUNT_ID,
    OANDA_API_TOKEN,
    OANDA_BASE_URL,
    OANDA_MAX_ORDER_UNITS,
)
from src.data.common import PAIRS

Side = Literal["buy", "sell"]


def _headers() -> dict[str, str]:
    if not OANDA_API_TOKEN:
        raise RuntimeError("OANDA_API_TOKEN not set in environment")
    return {
        "Authorization": f"Bearer {OANDA_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept-Datetime-Format": "RFC3339",
    }


def _account_id(account_id: str | None = None) -> str:
    aid = account_id or OANDA_ACCOUNT_ID
    if not aid:
        raise RuntimeError("OANDA_ACCOUNT_ID not set in environment")
    return aid


def _instrument(pair: str) -> str:
    if pair not in PAIRS:
        raise ValueError(f"Unknown pair {pair}; known: {list(PAIRS)}")
    return PAIRS[pair][1]


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=_headers(), timeout=15, base_url=OANDA_BASE_URL)


# -- Account --------------------------------------------------------------


async def get_account_summary(account_id: str | None = None) -> dict[str, Any]:
    """Balance, unrealized P&L, margin, NAV, open position/trade counts."""
    async with _client() as c:
        r = await c.get(f"/v3/accounts/{_account_id(account_id)}/summary")
        r.raise_for_status()
        return r.json()["account"]


# -- Pricing --------------------------------------------------------------


async def get_pricing(
    pairs: list[str], account_id: str | None = None
) -> list[dict[str, Any]]:
    """Current bid/ask per instrument."""
    instruments = ",".join(_instrument(p) for p in pairs)
    async with _client() as c:
        r = await c.get(
            f"/v3/accounts/{_account_id(account_id)}/pricing",
            params={"instruments": instruments},
        )
        r.raise_for_status()
        return r.json().get("prices", [])


# -- Positions / Trades ---------------------------------------------------


async def get_open_positions(account_id: str | None = None) -> list[dict[str, Any]]:
    async with _client() as c:
        r = await c.get(f"/v3/accounts/{_account_id(account_id)}/openPositions")
        r.raise_for_status()
        return r.json().get("positions", [])


async def get_open_trades(account_id: str | None = None) -> list[dict[str, Any]]:
    async with _client() as c:
        r = await c.get(f"/v3/accounts/{_account_id(account_id)}/openTrades")
        r.raise_for_status()
        return r.json().get("trades", [])


async def get_trade_history(
    account_id: str | None = None,
    count: int = 50,
    state: str = "CLOSED",
) -> list[dict[str, Any]]:
    async with _client() as c:
        r = await c.get(
            f"/v3/accounts/{_account_id(account_id)}/trades",
            params={"state": state, "count": count},
        )
        r.raise_for_status()
        return r.json().get("trades", [])


# -- Orders ---------------------------------------------------------------


async def place_market_order(
    pair: str,
    side: Side,
    units: int,
    take_profit: float | None = None,
    stop_loss: float | None = None,
    client_tag: str | None = None,
    account_id: str | None = None,
) -> dict[str, Any]:
    """Place a market order. Units are POSITIVE; side is 'buy' or 'sell'.
    OANDA uses signed units internally (positive=buy, negative=sell)."""
    if units <= 0:
        raise ValueError("units must be positive; pass side='buy' or 'sell'")
    if units > OANDA_MAX_ORDER_UNITS:
        raise ValueError(
            f"units {units} exceeds OANDA_MAX_ORDER_UNITS "
            f"({OANDA_MAX_ORDER_UNITS}); refusing to place"
        )

    signed_units = str(units if side == "buy" else -units)
    order: dict[str, Any] = {
        "type": "MARKET",
        "instrument": _instrument(pair),
        "units": signed_units,
        "timeInForce": "FOK",
        "positionFill": "DEFAULT",
    }
    if take_profit is not None:
        order["takeProfitOnFill"] = {"price": f"{take_profit:.5f}"}
    if stop_loss is not None:
        order["stopLossOnFill"] = {"price": f"{stop_loss:.5f}"}
    if client_tag:
        order["clientExtensions"] = {"tag": client_tag}

    async with _client() as c:
        r = await c.post(
            f"/v3/accounts/{_account_id(account_id)}/orders",
            json={"order": order},
        )
        r.raise_for_status()
        return r.json()


async def close_trade(
    trade_id: str,
    units: str = "ALL",
    account_id: str | None = None,
) -> dict[str, Any]:
    """Close an open trade fully (units='ALL') or partially (e.g. '500')."""
    async with _client() as c:
        r = await c.put(
            f"/v3/accounts/{_account_id(account_id)}/trades/{trade_id}/close",
            json={"units": units},
        )
        r.raise_for_status()
        return r.json()


async def cancel_order(
    order_id: str, account_id: str | None = None
) -> dict[str, Any]:
    async with _client() as c:
        r = await c.put(
            f"/v3/accounts/{_account_id(account_id)}/orders/{order_id}/cancel"
        )
        r.raise_for_status()
        return r.json()
