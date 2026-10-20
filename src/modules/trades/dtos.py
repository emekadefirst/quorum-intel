from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from src.common.base_dto import BaseDTO


class PlaceTrade(BaseModel):
    pair: str = Field(..., examples=["GBPUSD"])
    side: Literal["buy", "sell"]
    units: int = Field(..., gt=0, le=10_000_000)
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    llm_reasoning: Optional[str] = None
    source: Literal["manual", "agent"] = "manual"


class CloseTrade(BaseModel):
    units: str = Field("ALL", description="'ALL' or integer unit count as string")


class TradeDTO(BaseDTO):
    pair: str
    side: str
    units: int
    oanda_order_id: Optional[str] = None
    oanda_trade_id: Optional[str] = None
    fill_price: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    status: str
    close_price: Optional[float] = None
    realized_pl: Optional[float] = None
    closed_at: Optional[datetime] = None
    llm_reasoning: Optional[str] = None
    source: str


class PaginatedTradeDTO(BaseModel):
    page: int
    page_size: int
    total: int
    data: list[TradeDTO]


class AccountSummaryDTO(BaseModel):
    """Pass-through of OANDA account summary (we don't normalize all fields)."""

    data: dict[str, Any]
