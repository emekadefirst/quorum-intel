from fastapi import Body, Depends, HTTPException, Query

from src.common.base_router import base_router
from src.crypto.jwt import JwtService
from src.modules.account.models import Account
from src.modules.trades.dtos import (
    AccountSummaryDTO,
    CloseTrade,
    PaginatedTradeDTO,
    PlaceTrade,
    TradeDTO,
)
from src.modules.trades.services import TradesService

router = base_router(prefix="/api/trades", tags=["Trades"])


@router.get("/account")
async def account_summary(
    user: Account = Depends(JwtService.get_current_user),
) -> AccountSummaryDTO:
    try:
        return AccountSummaryDTO(data=await TradesService.account_summary())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OANDA error: {e}")


@router.get("/positions")
async def open_positions(
    user: Account = Depends(JwtService.get_current_user),
) -> list[dict]:
    try:
        return await TradesService.open_positions()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OANDA error: {e}")


@router.get("/open")
async def open_trades(
    user: Account = Depends(JwtService.get_current_user),
) -> list[dict]:
    try:
        return await TradesService.open_trades()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OANDA error: {e}")


@router.get("")
async def list_trades(
    pair: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: Account = Depends(JwtService.get_current_user),
) -> PaginatedTradeDTO:
    return await TradesService.list(
        account_id=str(user.id),
        pair=pair,
        status=status_filter,
        page=page,
        page_size=page_size,
    )


@router.post("", status_code=201)
async def place_trade(
    data: PlaceTrade,
    user: Account = Depends(JwtService.get_current_user),
) -> TradeDTO:
    try:
        return await TradesService.place(account_id=str(user.id), data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OANDA error: {e}")


@router.post("/{trade_id}/close")
async def close_trade(
    trade_id: str,
    data: CloseTrade = Body(default_factory=lambda: CloseTrade(units="ALL")),
    user: Account = Depends(JwtService.get_current_user),
) -> TradeDTO:
    try:
        trade = await TradesService.close(
            account_id=str(user.id), trade_id=trade_id, units=data.units
        )
        if trade is None:
            raise HTTPException(status_code=404, detail="Trade not found")
        return trade
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OANDA error: {e}")
