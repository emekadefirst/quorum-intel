from tortoise.expressions import Q

from src.common.base_repo import BaseRepository
from src.modules.trades.dtos import PaginatedTradeDTO, TradeDTO
from src.modules.trades.models import Trade


class TradeBOA(BaseRepository):
    def __init__(self) -> None:
        super().__init__(Trade)

    async def fetch(
        self,
        account_id: str,
        pair: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedTradeDTO:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be at least 1")

        query = Q(account_id=account_id)
        if pair:
            query &= Q(pair=pair)
        if status:
            query &= Q(status=status)

        total = await self.model.filter(query).count()
        rows = (
            await self.model.filter(query)
            .order_by("-created_at")
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        return PaginatedTradeDTO(
            page=page,
            page_size=page_size,
            total=total,
            data=[TradeDTO.model_validate(r, from_attributes=True) for r in rows],
        )
