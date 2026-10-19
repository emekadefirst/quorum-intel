from fastapi import HTTPException, Query, status

from src.common.base_router import base_router
from src.modules.news.service import NewsService

router = base_router(prefix="/api/news", tags=["News"])


@router.get("/digest")
async def get_digest(
    lookback_hours: float = Query(48, ge=1, le=168),
    max_items: int = Query(25, ge=1, le=100),
) -> dict:
    try:
        return await NewsService.get_digest(
            lookback_hours=lookback_hours, max_items=max_items
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to build news digest: {e}",
        )
