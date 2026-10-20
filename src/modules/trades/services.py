"""TradesService: thin orchestration around the broker + DB persistence.

Flow:
 1. Snapshot current quant+news so the trade's reasoning is auditable later
 2. Call the broker (Deriv, demo by default)
 3. Persist a Trade row with the broker's response + context

Active broker: Deriv. Swap `from src.data import deriv_trading as broker`
back to OANDA when/if OANDA accepts your region.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.data import deriv_trading as broker
from src.modules.news.service import NewsService
from src.modules.signals.service import SignalsService
from src.modules.trades.dtos import PaginatedTradeDTO, PlaceTrade, TradeDTO
from src.modules.trades.models import Trade
from src.modules.trades.repository import TradeBOA


class TradesService:
    repo = TradeBOA()

    # -- Account / market read-through --------------------------------------

    @classmethod
    async def account_summary(cls) -> dict[str, Any]:
        return await broker.get_account_summary()

    @classmethod
    async def pricing(cls, pairs: list[str]) -> list[dict[str, Any]]:
        return await broker.get_pricing(pairs)

    @classmethod
    async def open_positions(cls) -> list[dict[str, Any]]:
        return await broker.get_open_positions()

    @classmethod
    async def open_trades(cls) -> list[dict[str, Any]]:
        return await broker.get_open_trades()

    # -- Write operations ---------------------------------------------------

    @classmethod
    async def place(cls, account_id: str, data: PlaceTrade) -> TradeDTO:
        # 1. snapshot context (best-effort; never block the trade on this)
        quant: dict[str, Any] | None = None
        news: dict[str, Any] | None = None
        try:
            quant = SignalsService.get_current(pair=data.pair, interval="1h")
        except Exception:
            quant = None
        try:
            news = await NewsService.get_digest(max_items=5)
        except Exception:
            news = None

        # 2. place with the broker
        resp = await broker.place_market_order(
            pair=data.pair,
            side=data.side,
            units=data.units,
            take_profit=data.take_profit,
            stop_loss=data.stop_loss,
        )

        # Deriv's buy response has contract_id + buy_price when it fills.
        contract_id = resp.get("contract_id")
        buy_price = resp.get("buy_price")
        status = "open" if contract_id else "rejected"
        order = resp
        fill = {
            "tradeOpened": {"tradeID": str(contract_id) if contract_id else None},
            "price": buy_price,
        }

        # 3. persist audit row
        trade = await Trade.create(
            account_id=account_id,
            pair=data.pair,
            side=data.side,
            units=data.units,
            oanda_order_id=order.get("id"),
            oanda_trade_id=fill.get("tradeOpened", {}).get("tradeID"),
            fill_price=float(fill["price"]) if fill.get("price") else None,
            take_profit=data.take_profit,
            stop_loss=data.stop_loss,
            status=status,
            quant_snapshot=quant,
            news_snapshot=news,
            llm_reasoning=data.llm_reasoning,
            source=data.source,
        )
        return TradeDTO.model_validate(trade, from_attributes=True)

    @classmethod
    async def close(
        cls, account_id: str, trade_id: str, units: str = "ALL"
    ) -> TradeDTO | None:
        trade = await Trade.get_or_none(id=trade_id, account_id=account_id)
        if trade is None or not trade.oanda_trade_id:
            return None

        resp = await broker.close_trade(trade.oanda_trade_id, units=units)
        # Deriv's sell response has sold_for (close value) and transaction_id.
        sold_for = resp.get("sold_for")
        if sold_for is not None:
            trade.status = "closed"
            trade.close_price = float(sold_for)
            # Realized P&L approximation: close - open (stake). Deriv also returns profit
            # on contract settlement; refine later by querying profit_table.
            if trade.fill_price is not None:
                trade.realized_pl = float(sold_for) - float(trade.fill_price)
            trade.closed_at = datetime.now(timezone.utc)
            await trade.save()
        return TradeDTO.model_validate(trade, from_attributes=True)

    # -- Read -------------------------------------------------------------

    @classmethod
    async def list(
        cls,
        account_id: str,
        pair: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedTradeDTO:
        return await cls.repo.fetch(
            account_id=account_id,
            pair=pair,
            status=status,
            page=page,
            page_size=page_size,
        )
