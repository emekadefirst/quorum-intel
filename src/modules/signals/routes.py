from fastapi import HTTPException, Query, status

from src.common.base_router import base_router
from src.modules.signals.service import SignalsService

router = base_router(prefix="/api/signals", tags=["Signals"])


@router.get("/current")
async def current_signals(
    pair: str = Query("GBPUSD"),
    interval: str = Query("1h"),
) -> dict:
    try:
        return SignalsService.get_current(pair=pair, interval=interval)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to build insights: {e}",
        )
