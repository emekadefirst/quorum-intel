from fastapi import Request, Response
from tortoise.expressions import Q

from src.common.base_repo import ConflictError, NotFoundError
from src.crypto.jwt import JwtService
from src.crypto.password import PasswordManager
from src.modules.account.dtos import (
    AccountObjectDTO,
    CreateAccount,
    LoginAccount,
    PaginatedAccountDTO,
    UpdateAccount,
)
from src.modules.account.repository import AccountBOA


class AccountService:
    repo = AccountBOA()

    @classmethod
    async def login(
        cls, data: LoginAccount, request: Request, response: Response
    ) -> dict[str, str]:
        try:
            account = await cls.repo.get(email=data.email)
            if account is None:
                raise NotFoundError("Invalid email or password")
            PasswordManager.check_password(account.password, data.password)  # type: ignore[attr-defined]
            return JwtService.generate_tokens(
                subject={"id": str(account.id)},  # type: ignore[attr-defined]
                request=request,
                response=response,
            )
        except ValueError:
            raise NotFoundError("Invalid email or password")

    @classmethod
    async def create(cls, data: CreateAccount) -> AccountObjectDTO:
        try:
            existing = await cls.repo.get(Q(email=data.email) | Q(name=data.name))
            if existing:
                raise ConflictError("Account with this email or name already exists")
            payload = data.model_dump()
            payload["password"] = PasswordManager.set_password(payload["password"])
            account = await cls.repo.create(**payload)
            return AccountObjectDTO.model_validate(account, from_attributes=True)
        except ConflictError:
            raise

    @classmethod
    async def fetch(
        cls,
        id: str | None = None,
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedAccountDTO:
        return await cls.repo.fetch(
            id=id,
            search=search,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )

    @classmethod
    async def get_by_id(cls, id: str) -> AccountObjectDTO | None:
        result = await cls.repo.fetch(id=id, page_size=1)
        return result.data[0] if result.data else None

    @classmethod
    async def update(
        cls,
        id: str,
        data: UpdateAccount,
    ) -> AccountObjectDTO | None:
        account = await cls.repo.get(id=id)
        if account is None:
            return None

        values = data.model_dump(exclude_unset=True)
        if values:
            await cls.repo.update(account, **values)

        return await cls.get_by_id(id)

    @classmethod
    async def delete(cls, id: str) -> None:
        await cls.repo.delete(id)
