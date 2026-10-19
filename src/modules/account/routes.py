from fastapi import Depends, Request, Response

from src.common.base_router import base_router
from src.crypto.jwt import JwtService
from src.modules.account.dtos import (
    AccountObjectDTO,
    CreateAccount,
    LoginAccount,
    UpdateAccount,
)
from src.modules.account.models import Account
from src.modules.account.services import AccountService

router = base_router(prefix="/accounts", tags=["Accounts"])


@router.post("/login")
async def login(
    data: LoginAccount, request: Request, response: Response
) -> dict[str, str]:
    return await AccountService.login(data, request, response)


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"status": "ok"}


@router.post("", status_code=201)
async def create_account(data: CreateAccount) -> AccountObjectDTO:
    return await AccountService.create(data)


@router.get("/me")
async def get_current_user(
    user: Account = Depends(JwtService.get_current_user),
) -> AccountObjectDTO:
    return AccountObjectDTO.model_validate(user, from_attributes=True)


@router.patch("")
async def update_account(
    data: UpdateAccount,
    user: Account = Depends(JwtService.get_current_user),
) -> AccountObjectDTO | None:
    return await AccountService.update(str(user.id), data)


@router.delete("", status_code=204)
async def delete_account(
    user: Account = Depends(JwtService.get_current_user),
) -> None:
    await AccountService.delete(str(user.id))
