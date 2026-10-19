from tortoise.expressions import Q

from src.common.base_repo import BaseRepository
from src.modules.account.dtos import AccountObjectDTO, PaginatedAccountDTO
from src.modules.account.models import Account


class AccountBOA(BaseRepository):
    def __init__(self) -> None:
        super().__init__(Account)

    async def fetch(
        self,
        id: str | None = None,
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedAccountDTO:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be at least 1")

        query = Q()
        if id is not None:
            query &= Q(id=id)
        if search is not None:
            query &= Q(name__icontains=search) | Q(email__icontains=search)

        if is_active is not None:
            query &= Q(is_active=is_active)

        total = await self.model.filter(query).count()
        responses = await (
            self.model.filter(query).offset((page - 1) * page_size).limit(page_size)
        )

        return PaginatedAccountDTO(
            page=page,
            page_size=page_size,
            total=total,
            data=[
                AccountObjectDTO.model_validate(response, from_attributes=True)
                for response in responses
            ],
        )
