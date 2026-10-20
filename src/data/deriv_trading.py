"""Deriv v3 trading: account, pricing, portfolio, multiplier contracts.

Public function names match src/data/oanda_trading.py so swapping brokers is a
one-import change. Semantics differ in two places (documented inline):

 - OANDA trades FX with signed base-currency units. Deriv trades FX via
   multiplier contracts: `amount` is the stake (account currency), `multiplier`
   is leverage, `side` picks MULTUP (long) or MULTDOWN (short).
 - A Deriv "trade" is a contract; its `contract_id` is what we store in
   `oanda_trade_id` on the Trade model (sorry, the column name is historical).
"""

from __future__ import annotations

from typing import Any, Literal

from src.configs.data import DERIV_DEFAULT_MULTIPLIER, DERIV_MAX_STAKE
from src.data.common import PAIRS
from src.data.deriv_client import deriv_call, deriv_calls

Side = Literal["buy", "sell"]


def _symbol(pair: str) -> str:
    if pair not in PAIRS:
        raise ValueError(f"Unknown pair {pair}; known: {list(PAIRS)}")
    return PAIRS[pair][2]  # third slot = deriv symbol


# -- Account --------------------------------------------------------------


async def get_account_summary(account_id: str | None = None) -> dict[str, Any]:
    """Balance + account info. (account_id ignored: Deriv auth is token-scoped.)"""
    results = await deriv_calls([{"balance": 1}, {"get_account_status": 1}])
    bal = results[0].get("balance", {})
    status = results[1].get("get_account_status", {})
    return {
        "id": bal.get("loginid"),
        "currency": bal.get("currency"),
        "balance": float(bal.get("balance", 0)),
        "status": status.get("status", []),
        "raw": {"balance": bal, "status": status},
    }


# -- Pricing --------------------------------------------------------------


async def get_pricing(
    pairs: list[str], account_id: str | None = None
) -> list[dict[str, Any]]:
    """Latest bid/ask per pair. Deriv returns the latest tick (spot price)."""
    payloads = [
        {"ticks_history": _symbol(p), "end": "latest", "count": 1, "style": "ticks"}
        for p in pairs
    ]
    results = await deriv_calls(payloads)
    out: list[dict[str, Any]] = []
    for pair, r in zip(pairs, results):
        hist = r.get("history", {})
        prices = hist.get("prices") or []
        times = hist.get("times") or []
        spot = float(prices[-1]) if prices else None
        out.append(
            {
                "pair": pair,
                "symbol": _symbol(pair),
                "time": int(times[-1]) if times else None,
                "bid": spot,  # Deriv quotes mid as the tick price; broker spread applies on fill
                "ask": spot,
            }
        )
    return out


# -- Positions / Trades ---------------------------------------------------


async def get_open_positions(account_id: str | None = None) -> list[dict[str, Any]]:
    """Open contracts (Deriv doesn't aggregate by instrument; each contract is listed)."""
    r = await deriv_call({"portfolio": 1})
    return r.get("portfolio", {}).get("contracts", [])


async def get_open_trades(account_id: str | None = None) -> list[dict[str, Any]]:
    """Alias: Deriv's portfolio = open contracts = open trades."""
    return await get_open_positions(account_id)


async def get_trade_history(
    account_id: str | None = None,
    count: int = 50,
    state: str = "CLOSED",
) -> list[dict[str, Any]]:
    """Closed-trade history. `state` is ignored (Deriv's profit_table is closed-only)."""
    r = await deriv_call(
        {"profit_table": 1, "description": 1, "limit": count, "sort": "DESC"}
    )
    return r.get("profit_table", {}).get("transactions", [])


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
    """Buy a multiplier contract on `pair`.

    Mapping from OANDA-style args to Deriv:
      - `units` -> stake amount (in account currency)
      - `side='buy'` -> MULTUP (long), `side='sell'` -> MULTDOWN (short)
      - take_profit / stop_loss -> absolute price levels, forwarded as limit_order

    `units` of 1 means $1 stake; a 10 means $10 stake. Hard-capped by DERIV_MAX_STAKE.
    """
    if units <= 0:
        raise ValueError("units must be positive; pass side='buy' or 'sell'")
    stake = float(units)
    if stake > DERIV_MAX_STAKE:
        raise ValueError(
            f"stake {stake} exceeds DERIV_MAX_STAKE ({DERIV_MAX_STAKE}); refusing"
        )

    contract_type = "MULTUP" if side == "buy" else "MULTDOWN"
    proposal_req: dict[str, Any] = {
        "proposal": 1,
        "amount": stake,
        "basis": "stake",
        "contract_type": contract_type,
        "currency": "USD",
        "symbol": _symbol(pair),
        "multiplier": DERIV_DEFAULT_MULTIPLIER,
    }
    limit_order: dict[str, Any] = {}
    if take_profit is not None:
        limit_order["take_profit"] = float(take_profit)
    if stop_loss is not None:
        limit_order["stop_loss"] = float(stop_loss)
    if limit_order:
        proposal_req["limit_order"] = limit_order

    # Step 1: get a proposal (quote). Step 2: buy using the proposal id.
    results = await deriv_calls([proposal_req])
    proposal = results[0].get("proposal", {})
    proposal_id = proposal.get("id")
    if not proposal_id:
        raise RuntimeError(f"No proposal id returned: {results[0]}")

    buy_req = {"buy": proposal_id, "price": float(proposal.get("ask_price", stake))}
    buy_resp = await deriv_call(buy_req)
    return buy_resp.get("buy", buy_resp)


async def close_trade(
    trade_id: str,
    units: str = "ALL",
    account_id: str | None = None,
) -> dict[str, Any]:
    """Close a Deriv contract by its contract_id.
    `units` is ignored - Deriv contracts are closed whole."""
    r = await deriv_call({"sell": int(trade_id), "price": 0})
    return r.get("sell", r)


async def cancel_order(
    order_id: str, account_id: str | None = None
) -> dict[str, Any]:
    """Cancel a pending order. Deriv `cancel` applies to time-locked contracts;
    for immediate multiplier contracts, use close_trade instead."""
    r = await deriv_call({"cancel": int(order_id)})
    return r.get("cancel", r)
